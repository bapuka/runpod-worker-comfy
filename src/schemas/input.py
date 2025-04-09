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
    "images": [
        {
            "name": "input-01.png",
            "image": "base64string",
        }
    ]
}