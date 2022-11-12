import logging
from dotenv import load_dotenv
import azure.functions as func
import os
import MeCab
from googletrans import Translator
import replicate
import ipadic
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    text = req.params.get("content")
    try:
        translator = Translator(service_urls=['translate.googleapis.com'])
    except:
        logging.info("translator failed")
    try:
        tokenizer = MeCab.Tagger(ipadic.MECAB_ARGS)
    except:
        logging.info("tokenizer failed")
    node = tokenizer.parseToNode(text)
    logging.info(node)
    words = []
    while node:
        hinshi = node.feature.split(",")[0]
        if hinshi in ["名詞", "動詞"]:
            origin = node.feature.split(",")[6]
            dst = translator.translate(origin, dest="en")
            words.append(dst.text)
        node = node.next

    logging.info(f"{words}")

    try:    
        model = replicate.models.get("stability-ai/stable-diffusion")
        version = model.versions.get(
            "8abccf52e7cba9f6e82317253f4a3549082e966db5584e92c808ece132037776")
    except: 
        logging.info("replicate Error")
    prompt = " ".join(words)
    logging.info(prompt)
    output = version.predict(prompt=prompt)
    return func.HttpResponse(
        json.dumps({
            "output": output
        })
    )
