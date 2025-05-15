INPUT_SCHEMA = {
    'server': {
        'type': str,
        'required': True,
        'default': 'comfyui',
        'description': 'Server type to use for processing. Options: comfyui, python, custom. Default: comfyui.',
        },
    'workflow': {
        'type': str,
        'required': False,
        'default': 'txt2img',
        'constraints': lambda workflow: workflow in [
            'default',
            'txt2img',
            "txt2imgSceneSDXL",
            'img2imgPersona', 
            'upscale',
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
        'default': None,
        'description': 'Unique identifier for batch processing. When provided, images will be uploaded only once per batch.'
    }
}
