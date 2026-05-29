/* ScummVM - Graphic Adventure Engine
 *
 * ScummVM is the legal property of its developers, whose names
 * are too numerous to list here. Please refer to the COPYRIGHT
 * file distributed with this source distribution.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#include "backends/graphics/opengl/shader.h"
#include "graphics/opengl/debug.h"

#if !USE_FORCED_GLES

namespace Common {
DECLARE_SINGLETON(OpenGL::ShaderManager);
}

namespace OpenGL {

namespace {

#pragma mark - Builtin Shader Sources -

const char *const g_defaultShaderAttributes[] = {
	"position", "texCoordIn", "blendColorIn", nullptr
};

const char *const g_defaultVertexShader =
	"attribute vec4 position;\n"
	"attribute vec2 texCoordIn;\n"
	"attribute vec4 blendColorIn;\n"
	"\n"
	"uniform mat4 projection;\n"
	"\n"
	"varying vec2 texCoord;\n"
	"varying vec4 blendColor;\n"
	"\n"
	"void main(void) {\n"
	"\ttexCoord    = texCoordIn;\n"
	"\tblendColor  = blendColorIn;\n"
	"\tgl_Position = projection * position;\n"
	"}\n";

const char *const g_defaultFragmentShader =
	"varying vec2 texCoord;\n"
	"varying vec4 blendColor;\n"
	"\n"
	"uniform sampler2D shaderTexture;\n"
	"\n"
	"void main(void) {\n"
	"\tgl_FragColor = blendColor * texture2D(shaderTexture, texCoord);\n"
	"}\n";

const char *const g_lanczosFragmentShader =
	"varying vec2 texCoord;\n"
	"varying vec4 blendColor;\n"
	"\n"
	"uniform sampler2D shaderTexture;\n"
	"\n"
	"// Lanczos-2 area sampling for high-quality downscaling\n"
	"void main(void) {\n"
	"\tvec2 texelStep = vec2(1.0 / 2560.0, 1.0 / 1920.0);\n"
	"\tvec2 dx = dFdx(texCoord);\n"
	"\tvec2 dy = dFdy(texCoord);\n"
	"\tvec2 pixelStep = vec2(length(dx), length(dy));\n"
	"\tvec2 scale = pixelStep / texelStep;\n"
	"\tfloat maxScale = max(scale.x, scale.y);\n"
	"\t// 1:1 or upscaling -> simple sample (fast path)\n"
	"\tif (maxScale <= 1.0) {\n"
	"\t\tgl_FragColor = blendColor * texture2D(shaderTexture, texCoord);\n"
	"\t\treturn;\n"
	"\t}\n"
	"\t// Downscaling: Lanczos-2 weighted area sampling\n"
	"\tint radius = int(ceil(maxScale * 2.0));\n"
	"\tif (radius > 6) radius = 6;\n"
	"\tvec4 sum = vec4(0.0);\n"
	"\tfloat totalWeight = 0.0;\n"
	"\tfor (int y = -6; y <= 6; y++) {\n"
	"\t\tif (y < -radius || y > radius) continue;\n"
	"\t\tfor (int x = -6; x <= 6; x++) {\n"
	"\t\t\tif (x < -radius || x > radius) continue;\n"
	"\t\t\tvec2 off = vec2(float(x), float(y));\n"
	"\t\t\tfloat d = length(off) / maxScale;\n"
	"\t\t\tfloat w;\n"
	"\t\t\tif (d < 0.001) {\n"
	"\t\t\t\tw = 1.0;\n"
	"\t\t\t} else if (d < 2.0) {\n"
	"\t\t\t\tfloat pix = 3.14159265 * d;\n"
	"\t\t\t\tw = sin(pix) * sin(pix * 0.5) / (pix * pix * 0.5);\n"
	"\t\t\t} else {\n"
	"\t\t\t\tw = 0.0;\n"
	"\t\t\t}\n"
	"\t\t\tvec2 sc = texCoord + off * texelStep;\n"
	"\t\t\tsum += texture2D(shaderTexture, sc) * w;\n"
	"\t\t\ttotalWeight += w;\n"
	"\t\t}\n"
	"\t}\n"
	"\tif (totalWeight > 0.0)\n"
	"\t\tgl_FragColor = blendColor * (sum / totalWeight);\n"
	"\telse\n"
	"\t\tgl_FragColor = blendColor * texture2D(shaderTexture, texCoord);\n"
	"}\n";

const char *const g_lookUpFragmentShader =
	"varying vec2 texCoord;\n"
	"varying vec4 blendColor;\n"
	"\n"
	"uniform sampler2D shaderTexture;\n"
	"uniform sampler2D palette;\n"
	"\n"
	"const float scaleFactor = 255.0 / 256.0;\n"
	"const float offsetFactor = 1.0 / (2.0 * 256.0);\n"
	"\n"
	"void main(void) {\n"
	"\tvec4 index = texture2D(shaderTexture, texCoord);\n"
	"\tgl_FragColor = blendColor * texture2D(palette, vec2(index.a * scaleFactor + offsetFactor, 0.0));\n"
	"}\n";

} // End of anonymous namespace

ShaderManager::ShaderManager() {
	for (int i = 0; i < ARRAYSIZE(_builtIn); ++i) {
		_builtIn[i] = nullptr;
	}
}

ShaderManager::~ShaderManager() {
	for (int i = 0; i < ARRAYSIZE(_builtIn); ++i) {
		delete _builtIn[i];
	}
}

void ShaderManager::notifyDestroy() {
	for (int i = 0; i < ARRAYSIZE(_builtIn); ++i) {
		delete _builtIn[i];
		_builtIn[i] = nullptr;
	}
}

void ShaderManager::notifyCreate() {
	// Ensure everything is destroyed
	notifyDestroy();

	_builtIn[kDefault] = Shader::fromStrings("default", g_defaultVertexShader, g_defaultFragmentShader, g_defaultShaderAttributes, 110);
	_builtIn[kLanczos] = Shader::fromStrings("lanczos", g_defaultVertexShader, g_lanczosFragmentShader, g_defaultShaderAttributes, 110);
	_builtIn[kCLUT8LookUp] = Shader::fromStrings("clut8lookup", g_defaultVertexShader, g_lookUpFragmentShader, g_defaultShaderAttributes, 110);
	_builtIn[kCLUT8LookUp]->setUniform("palette", 1);

	for (uint i = 0; i < kMaxUsages; ++i) {
		_builtIn[i]->setUniform("shaderTexture", 0);
	}
}

Shader *ShaderManager::query(ShaderUsage shader) const {
	if (shader == kMaxUsages) {
		warning("OpenGL: ShaderManager::query used with kMaxUsages");
		return nullptr;
	}

	assert(_builtIn[shader]);
	return _builtIn[shader]->clone();
}

} // End of namespace OpenGL

#endif // !USE_FORCED_GLES
