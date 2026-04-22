import phonenumbers
from pydantic import BaseModel, field_validator


def _validate_e164(phone: str) -> str:
    try:
        parsed = phonenumbers.parse(phone, None)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        raise ValueError("Phone must be in E.164 format (e.g. +79001234567)")


class SendCodeRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def phone_e164(cls, v: str) -> str:
        return _validate_e164(v)


class VerifyCodeRequest(BaseModel):
    phone: str
    code: str

    @field_validator("phone")
    @classmethod
    def phone_e164(cls, v: str) -> str:
        return _validate_e164(v)

    @field_validator("code")
    @classmethod
    def code_format(cls, v: str) -> str:
        if len(v) != 6:
            raise ValueError("Code must be exactly 6 digits")
        if not v.isdigit():
            raise ValueError("Code must contain digits only")
        return v


class RefreshRequest(BaseModel):
    refresh_token: str


class MessageResponse(BaseModel):
    message: str


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class AccessTokenResponse(BaseModel):
    access_token: str
    expires_in: int


class ErrorResponse(BaseModel):
    code: str
    message: str
