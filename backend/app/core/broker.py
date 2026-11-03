import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker

from app.core.config import RABBITMQ_URL


rabbitmq_broker = RabbitmqBroker(
    url=RABBITMQ_URL,
    confirm_delivery=True,
)

dramatiq.set_broker(rabbitmq_broker)
