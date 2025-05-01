import pika
import json

def send_medication_request(prescription_data):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
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
