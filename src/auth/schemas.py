from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

# request bodies

class SignUpSchema(BaseModel):
    username: str = Field(..., min_length=3, example="rameesah")
    email: EmailStr = Field(..., example="rameesah@leeds.ac.uk")
    password: str = Field(..., min_length=6, example="password123")


class SignInSchema(BaseModel):
    username: str = Field(..., example="rameesah")
    password: str = Field(..., example="password123")


# response

class AuthResponseSchema(BaseModel):
    access_token: str = Field(..., description="JWT — use as Bearer token in protected routes")
    token_type: str = Field(default="bearer")


class UserProfileSchema(BaseModel):
    id: UUID
    username: str
    email: str
    role: str

    model_config = {"from_attributes": True}


#internal JWT payload

class JwtPayload(BaseModel):
    sub: str        # user id
    username: str
    role: str       # USER or ADMIN