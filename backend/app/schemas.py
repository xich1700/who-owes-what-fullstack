from pydantic import BaseModel, Field


# ---- Auth ----
class SignupRequest(BaseModel):
    username: str
    password: str = Field(min_length=4)
    security_question: str
    security_answer: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordLookup(BaseModel):
    username: str


class ForgotPasswordReset(BaseModel):
    username: str
    security_answer: str
    new_password: str = Field(min_length=4)


# ---- Groups ----
class GroupCreate(BaseModel):
    name: str
    currency: str = "EUR"


class GroupOut(BaseModel):
    id: str
    name: str
    currency: str
    closed: bool
    share_token: str

    class Config:
        from_attributes = True


# ---- People ----
class PersonCreate(BaseModel):
    name: str


class PersonOut(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


# ---- Expenses ----
class ExpenseCreate(BaseModel):
    payer_id: str
    amount: float = Field(gt=0)
    label: str = ""
    is_recurring: bool = False
    beneficiary_weights: dict[str, float]  # {person_id: weight}


class ExpenseOut(BaseModel):
    id: str
    payer_id: str
    amount: float
    label: str
    is_recurring: bool
    beneficiaries: dict[str, float]


# ---- Repayments ----
class RepaymentCreate(BaseModel):
    from_person_id: str
    to_person_id: str
    amount: float = Field(gt=0)


class RepaymentOut(BaseModel):
    id: str
    from_person_id: str
    to_person_id: str
    amount: float

    class Config:
        from_attributes = True


# ---- Totals ----
class PersonBalance(BaseModel):
    person_id: str
    name: str
    paid: float
    share: float
    outstanding: float


class SettlementTransaction(BaseModel):
    from_id: str
    from_name: str
    to_id: str
    to_name: str
    amount: float


class TotalsOut(BaseModel):
    total_spent: float
    currency: str
    balances: list[PersonBalance]
    settlement_plan: list[SettlementTransaction]


# ---- Natural-language expense parsing ----
class ParseExpenseRequest(BaseModel):
    sentence: str


class ParseExpenseResult(BaseModel):
    ok: bool
    payer_id: str | None = None
    payer_name: str | None = None
    amount: float | None = None
    label: str | None = None
    beneficiary_ids: list[str] | None = None
    error: str | None = None


# ---- Receipt scanning ----
class ScanReceiptResult(BaseModel):
    amount: float
    label: str
