import pika
import json
import os
from dotenv import load_dotenv
load_dotenv()


def send_medication_request(prescription_data):
    rabbitmq_url = os.getenv('RABBITMQ_URL')
    connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
    channel = connection.channel()

    channel.queue_declare(queue='medication_requests', durable=True)

    message = json.dumps(prescription_data)
    channel.basic_publish(
        exchange='',
        routing_key='medication_requests',
        body=message,
        properties=pika.BasicProperties(delivery_mode=2)  # make message persistent
    )

    connection.close()
