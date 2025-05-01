import pika
import json
from flask_mysqldb import MySQL
import MySQLdb

db_config = {
    'host': '34.148.167.204',
    'user': 'root',
    'passwd': 'root',
    'db': 'clinic_db'
}

def insert_prescription(appt_id, medicine_id, quantity):
    conn = MySQLdb.connect(**db_config)
    cursor = conn.cursor()
    
    query = """
    INSERT INTO PATIENT_PRESCRIPTION (appt_id, medicine_id, quantity, picked_up, filled, created_at, updated_at)
    VALUES (%s, %s, %s, 0, 0, NOW(), NOW())
    """
    cursor.execute(query, (appt_id, medicine_id, quantity))
    conn.commit()
    cursor.close()
    conn.close()

def callback(ch, method, properties, body):
    data = json.loads(body)
    print("Received prescription request:", data)
    
    try:
        insert_prescription(
            appt_id=data['appt_id'],
            medicine_id=data['medicine_id'],
            quantity=data['quantity']
        )
        print("Inserted prescription.")
    except Exception as e:
        print(f"Failed to insert prescription: {e}")
        # Optionally, publish the message to a 'dead-letter' queue or retry mechanism.
    
    ch.basic_ack(delivery_tag=method.delivery_tag)


def start_consumer():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='medication_requests', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='medication_requests', on_message_callback=callback)

    print(" [*] Waiting for medication requests. To exit press CTRL+C")
    channel.start_consuming()

if __name__ == '__main__':
    start_consumer()
