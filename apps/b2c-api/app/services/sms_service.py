import logging

logger = logging.getLogger(__name__)


class MockSmsService:
    async def send_otp(self, phone: str, code: str) -> None:
        logger.info("SMS OTP for %s: %s", phone, code)


sms_service = MockSmsService()
