INPUT_SCHEMA = {
    'workflow': {
        'type': str,
        'required': False,
        'default': 'txt2img',
        'constraints': lambda workflow: workflow in [
            'default',
            'txt2img',
            'img2imgPersona',
            'custom'
        ]
    },
    'payload': {
        'type': dict,
        'required': True
    },
    "images": {
        'type': list,
        'required': False,
        'default': []
    },
    "batchId": {
        'type': str,
        'required': False,
        'description': 'Unique identifier for batch processing. When provided, images will be uploaded only once per batch.'
    }
}
