# main.py
from fastapi import FastAPI, HTTPException
from sqlmodel import Field, SQLModel, create_engine, Session, select
from typing import Optional, List
from datetime import datetime, date
import os
from sse_starlette.sse import EventSourceResponse
import asyncio
from dotenv import load_dotenv


load_dotenv()
app = FastAPI()

# Database setup
DATABASE_URL = os.getenv("postgresql+psycopg2://admin:123@localhost:5432/mydb")
engine = create_engine(DATABASE_URL, echo=True)




# Employee table
class Employee(SQLModel, table=True):
    pg_id: Optional[int] = Field(default=None, primary_key=True)
    sys_id: Optional[str] = Field(default=None)
    first_name: str
    second_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    date_of_birth: Optional[date] = None
    department: Optional[str] = None
    manager: Optional[int] = Field(default=None, foreign_key="employee.pg_id")
    pg_created_at: datetime = Field(default_factory=datetime.utcnow)
    pg_soft_delete: bool = Field(default=False)

# Create DB
SQLModel.metadata.create_all(engine)

# GET endpoint to list all employees
@app.get("/employees", response_model=List[Employee])
def get_employees():
    with Session(engine) as session:
        statement = select(Employee).where(Employee.pg_soft_delete == False)
        return session.exec(statement).all()

# POST endpoint to add a new employee
@app.post("/employees", response_model=Employee)
def add_employee(employee: Employee):
    with Session(engine) as session:
        session.add(employee)
        session.commit()
        session.refresh(employee)
        return employee
    
last_seen_id = 0  # global tracker

async def stream_new_lines():
    global last_seen_id

    while True:
        with Session(engine) as session:
            statement = select(Employee).where(
                Employee.pg_id > last_seen_id,
                Employee.pg_soft_delete == False
            )
            new_employees = session.exec(statement).all()

            for emp in new_employees:
                last_seen_id = max(last_seen_id, emp.pg_id)
                yield f"data: {emp.model_dump()}\n\n"

        await asyncio.sleep(0.5)

@app.get("/stream")
async def sse_endpoint():
    return EventSourceResponse(stream_new_lines())
    