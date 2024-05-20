from faker import Faker
from sqlalchemy.orm import Session
from user.models import User
from company.models import Company
from poll.models import Poll
import random
from core.security import get_password_hash
from db.session import SessionLocal, db_session
from datetime import datetime

fake = Faker('ru_RU')


def generate_inn():
    """ Генерация ИНН"""

    inn = "56"
    for _ in range(8):
        inn += str(random.randint(0, 9))
    return inn


def generate_phone_number():
    """Генерация номера телефона в формате +7 (XXX) XXX-XX-XX"""

    phone = "+7 (9" + str(random.randint(10, 99)) + ") "
    phone += "".join([str(random.randint(0, 9)) for _ in range(3)]) + "-"
    phone += "".join([str(random.randint(0, 9)) for _ in range(2)]) + "-"
    phone += "".join([str(random.randint(0, 9)) for _ in range(2)])
    return phone


def generate_address():
    """Генерация адреса в формате Область, город, город, улица, дом, индекс"""

    regions = ["Оренбургская обл."]
    cities = ["г. Орск", "г. Оренбург"]

    region = random.choice(regions)
    city = random.choice(cities)
    house_number = random.randint(1, 100)
    postal_code = random.randint(100000, 200000)
    address = f"{region}, {city}, {fake.street_name()}, д. {house_number}, {postal_code}"
    return address


def generate_company_name():
    """Генерация названия компании"""

    moau = ["МОАУ", "МБОУ"]
    name = ["СОШ", "Лицей"]
    number = random.randint(1, 100)
    return f"{moau[random.randint(0, 1)]} {name[random.randint(0, 1)]} {number}"


def create_users(db: Session, num_users: int):
    """Создание фейковых пользвоателей

    :param db:
    :param num_users:
    """

    users = []
    start_date = datetime(2024, 1, 1)
    end_date = datetime.now()
    for _ in range(num_users):
        user = User(
            email=fake.email(),
            hashed_password=get_password_hash('123456'),
            full_name=fake.name(),
            is_active=True,
            created_at=fake.date_time_between(start_date=start_date, end_date=end_date)
        )
        db.add(user)
        users.append(user)
        print(f"User {user.full_name} created")
    db.commit()
    return users


def create_companies(db: Session, num_companies: int, users):
    """Создание фейковых компаний

    :param db:
    :param num_companies: Количество компаний
    :param users Список пользователей
    """

    user_index = 0
    for _ in range(num_companies):
        address = generate_address()
        name = generate_company_name()
        licenses = random.randint(1, 10)
        start_date = datetime(2024, 1, 1)
        end_date = datetime.now()
        created_at = fake.date_time_between(start_date=start_date, end_date=end_date)
        company = Company(
            name=name,
            full_name=name,
            inn=generate_inn(),
            legal_address=address,
            actual_address=address,
            phone=generate_phone_number(),
            director_name=fake.name(),
            admin_name=fake.name(),
            admin_email=fake.email(),
            licenses=licenses,
            created_at=created_at
        )
        db.add(company)
        db.commit()
        print(f"Comapny {company.full_name} created")

        # Связываем пользователей с компанией, не превышая количество лицензий
        num_users_for_company = min(licenses, len(users) - user_index)
        for _ in range(num_users_for_company):
            user = users[user_index]
            user.company_id = company.id
            db.add(user)
            user_index += 1
        db.commit()

    db.commit()


def main():
    db = SessionLocal()
    users = create_users(db, 200)
    create_companies(db, 50, users)
    db.close()


if __name__ == "__main__":
    main()

