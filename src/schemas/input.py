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
            'upscaleSDXL',
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
        # 'default': "",
        'description': 'Unique identifier for batch processing. When provided, images will be uploaded only once per batch.'
    },
    "gdrivePath": {
        'type': str,
        'required': False,
        # 'default': "",
        'description': 'Google Drive path for saving images. If provided, images will be saved to this path.'
    }
}
