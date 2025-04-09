#!/usr/bin/env python3
from util import post_request
import random

if __name__ == '__main__':
    payload = {
        "input": {
            "workflow": "img2imgPersona",
            "payload": {
                "seed": random.randrange(1, 1000000),
                "steps": 30,
                "cfg_scale": 5,
                "sampler_name": "dpm_2",
                "scheduler": "karras",
                "ckpt_name": "sdxl/CHEYENNE_v20.safetensors",
                "batch_size": 4,
                "width": 824,
                "height": 1168,
                "prompt": "score_9, score_8_up, score_7_up, (a 5 year old little Asian girl:1.5) black hair with pigtails, chubby, wearing cozy winter pajamas, (detailed facial features:1.3), sparkly eager eyes, in (cozy bedroom:1.5), magical computer mouse (gleaming with ethereal blue aura:1.3), floating slightly above table, (soft glowing red button:1.2), (magical sparkles in blue and silver:1.3), minecraft blocks floating around as particles, warm home interior background, mystical atmosphere, mood is cozy,\ndetailed artwork, Ghibli style, childrens book illustration, inkscape, whimsical, perfect details, 8k, with incredible vibrant colors, ray tracing, dynamic epic composition, blur background",
                "negative_prompt": "score_6, score_5, score_4, worst quality:1.4, low quality:1.4, easynegative, negative_hand-neg, animal ear, chinese, kanji, breast, cropped, watermark, (low quality, worst quality:1.4), (bad anatomy), monochrome,(long body), bad anatomy , liquid body, malformed, mutated, anatomical nonsense ,bad proportions, uncoordinated body, unnatural body, ugly, gross proportions, disfigured, deformed,  mutation, poorly drawn , bad hand, mutated hand, bad fingers, mutated finger, freckles, mole, nude, nsfw"
            },
            "images": [
                {
                    "name": "input-01.png",
                    "image": ""
                }                
            ],            
        }
    }

post_request(payload)
