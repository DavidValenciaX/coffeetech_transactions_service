from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TransactionStates(Base):
    __tablename__ = 'transaction_states'
    transaction_state_id = Column(Integer, primary_key=True)
    name = Column(String(45), nullable=False, unique=True)
    transactions = relationship("Transactions", back_populates="state")
    
class TransactionTypes(Base):
    __tablename__ = 'transaction_types'

    transaction_type_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

    # Relaciones
    categories = relationship("TransactionCategories", back_populates="transaction_type")

class TransactionCategories(Base):
    __tablename__ = 'transaction_categories'
    __table_args__ = (UniqueConstraint('name', 'transaction_type_id'),)

    transaction_category_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    transaction_type_id = Column(Integer, ForeignKey('transaction_types.transaction_type_id'), nullable=False)

    # Relaciones
    transaction_type = relationship("TransactionTypes", back_populates="categories")
    transactions = relationship("Transactions", back_populates="transaction_category")

class Transactions(Base):
    __tablename__ = 'transactions'

    transaction_id = Column(Integer, primary_key=True)
    plot_id = Column(Integer, ForeignKey('plots.plot_id'), nullable=False)
    description = Column(String(255), nullable=True)
    transaction_date = Column(Date, nullable=False)
    transaction_state_id = Column(Integer, ForeignKey('transaction_states.transaction_state_id'), nullable=False)
    value = Column(Numeric(15, 2), nullable=False)
    transaction_category_id = Column(Integer, ForeignKey('transaction_categories.transaction_category_id'), nullable=False)
    creator_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)

    # Relaciones
    plot = relationship("Plots", back_populates="transactions")
    transaction_category = relationship("TransactionCategories", back_populates="transactions")
    state = relationship("TransactionStates", back_populates="transactions")
    creator = relationship("Users", back_populates="created_transactions")
