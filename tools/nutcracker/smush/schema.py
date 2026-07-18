DATA: set[str] = set()

RAWD = '____'  # Collect rest of chunk as raw data

SCHEMA = {
    'ANIM': {'AHDR', 'FRME'},
    'AHDR': DATA,
    'FRME': {
        'FTCH',
        'IACT',
        'XPAL',
        'TEXT',
        'STOR',
        'FOBJ',
        'NPAL',
        'TRES',
        'PSAD',
        'SKIP',
        'ZFOB',  # Zlib Compressed frame object
    },
    'FTCH': DATA,
    'IACT': DATA,
    'XPAL': DATA,
    'TEXT': DATA,
    'STOR': DATA,
    'FOBJ': DATA,
    'NPAL': DATA,
    'TRES': DATA,
    'PSAD': DATA,
    'SKIP': DATA,
    'ZFOB': DATA,  # Zlib Compressed frame object
}
