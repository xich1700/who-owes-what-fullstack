import uuid

from sqlalchemy import Column, String, Float, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


def new_id() -> str:
    return uuid.uuid4().hex


class Manager(Base):
    __tablename__ = "managers"

    id = Column(String, primary_key=True, default=new_id)
    username = Column(String, unique=True, nullable=False, index=True)
    salt = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    security_question = Column(String, nullable=True)
    security_answer_salt = Column(String, nullable=True)
    security_answer_hash = Column(String, nullable=True)

    groups = relationship("Group", back_populates="manager", cascade="all, delete-orphan")


class Group(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True, default=new_id)
    manager_id = Column(String, ForeignKey("managers.id"), nullable=False)
    name = Column(String, nullable=False)
    share_token = Column(String, unique=True, nullable=False, index=True)
    currency = Column(String, nullable=False, default="EUR")
    closed = Column(Boolean, nullable=False, default=False)

    manager = relationship("Manager", back_populates="groups")
    people = relationship("Person", back_populates="group", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="group", cascade="all, delete-orphan")
    repayments = relationship("Repayment", back_populates="group", cascade="all, delete-orphan")


class Person(Base):
    __tablename__ = "people"

    id = Column(String, primary_key=True, default=new_id)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    name = Column(String, nullable=False)

    group = relationship("Group", back_populates="people")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String, primary_key=True, default=new_id)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    payer_id = Column(String, ForeignKey("people.id"), nullable=False)
    amount = Column(Float, nullable=False)
    label = Column(String, nullable=True)
    is_recurring = Column(Boolean, nullable=False, default=False)

    group = relationship("Group", back_populates="expenses")
    beneficiaries = relationship("ExpenseBeneficiary", back_populates="expense", cascade="all, delete-orphan")


class ExpenseBeneficiary(Base):
    __tablename__ = "expense_beneficiaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expense_id = Column(String, ForeignKey("expenses.id"), nullable=False)
    person_id = Column(String, ForeignKey("people.id"), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)

    expense = relationship("Expense", back_populates="beneficiaries")


class Repayment(Base):
    __tablename__ = "repayments"

    id = Column(String, primary_key=True, default=new_id)
    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    from_person_id = Column(String, ForeignKey("people.id"), nullable=False)
    to_person_id = Column(String, ForeignKey("people.id"), nullable=False)
    amount = Column(Float, nullable=False)

    group = relationship("Group", back_populates="repayments")
