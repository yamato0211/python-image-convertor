import logging
import azure.functions as func
import os
import MeCab
from googletrans import Translator
import replicate
import ipadic
import json
from dotenv import find_dotenv, load_dotenv


class TableEntitySamples(object):
    def __init__(self):
        load_dotenv(find_dotenv())
        self.access_key = os.getenv("TABLES_PRIMARY_STORAGE_ACCOUNT_KEY")
        self.endpoint_suffix = os.getenv("TABLES_STORAGE_ENDPOINT_SUFFIX")
        self.account_name = os.getenv("TABLES_STORAGE_ACCOUNT_NAME")
        self.connection_string = "DefaultEndpointsProtocol=https;AccountName={};AccountKey={};EndpointSuffix={}".format(
            self.account_name, self.access_key, self.endpoint_suffix
        )

    def update_entities(self, userId:str, diaryDate:str, output):
        # Instantiate a table client
        from azure.data.tables import TableClient
        from azure.data.tables import UpdateMode

        logging.info(f"{self.connection_string}")
        with TableClient.from_connection_string(self.connection_string, table_name="diary") as table:

            # Create the table and Table Client
            #table.create_table()

            try:
                logging.info(f"userId: {userId}")
                logging.info(userId + "-" + diaryDate)
                words = diaryDate.split("-")
                try:
                    got_entity = table.get_entity(partition_key=words[0]+"-"+words[1], row_key=userId + "-" + diaryDate)
                except:
                    logging.info("get_entity_error")
                logging.info(f"{got_entity}")
                # [START update_entity]
                # Update the entity
                got_entity["ImageUrl"] = output[0]
                table.update_entity(mode=UpdateMode.REPLACE, entity=got_entity)
                # [END update_entity]
            finally:
                # Delete the table
                #table.delete_table()
                pass


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    req_json = req.get_json()
    content = req_json.get("content")
    userId = req_json.get("userId")
    logging.info(f"{userId}")
    diaryDate = req_json.get("diaryDate")
    logging.info(f"{diaryDate}")
    
    try:
        translator = Translator(service_urls=['translate.googleapis.com'])
    except:
        logging.info("translator failed")
    try:
        tokenizer = MeCab.Tagger(ipadic.MECAB_ARGS)
    except:
        logging.info("tokenizer failed")
    node = tokenizer.parseToNode(content)
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
    try:
        sample = TableEntitySamples()
    except:
        logging.info("TableEntitySamples Error")
    try:
        sample.update_entities(userId,diaryDate,output)
    except:
        logging.info("update_entities_error")

    return func.HttpResponse(
        json.dumps({
            "output": output
        })
    )
