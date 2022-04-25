u"""
Модуль выполняющий роль сервера\r\n
Для запуска сервера необходимо настроить конфигурационный файл config_server.yaml
"""
import decimal
import hashlib
import struct
import threading
import uuid
from threading import Thread
import yaml
from sqlalchemy import create_engine, Integer, String, Column, Date, ForeignKey, Numeric, Boolean
from sqlalchemy.ext.declarative import declarative_base
import socket
import json
from sqlalchemy.orm import Session, relationship
import logging.config
import datetime
import tarantool
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from functools import wraps
import pika


with open('config_server') as config_server:
    config = yaml.safe_load(config_server)

#########################################################################################
logging.config.dictConfig(config['logger_settings'])
logger = logging.getLogger('server')
#########################################################################################



try:
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='server_queue')
    connection_tarantool = tarantool.connect(config['connection_string_tarantool_ip'],
                                             config['connection_string_tarantool_port'])
    tarantool_space = connection_tarantool.space('user_token')
    db_engine = create_engine(config['connection_string'])
    db_engine.connect()
    Base = declarative_base()
    session_factory = sessionmaker(bind=db_engine)
    session = scoped_session(session_factory)
except tarantool.error.NetworkError:
    logger.error('Tarantool не подключен!!')
    exit()
except pika.exceptions.AMQPConnectionError:
    logger.error('RabbitMQ не подключен!!')
    exit()
except Exception as e:
    logger.error(e)
    exit()

salt = config['salt']


#########################################################################################
def object_to_dict(obj):
    """
    Метод для преобразования объекта класса в словарь\r\n
    Параметры:\r\n
        obj: объект какого-либо класса\r\n
    """
    return {x.name: getattr(obj, x.name)
            for x in obj.__table__.columns}

#########################################################################################
def dict_to_object(obj, dict):
    """
    Метод для преобразования словаря в объект класса\r\n
    Параметры:\r\n
        obj: объект какого-либо класса\r\n
        dict: словарь\r\n
    """
    for x in obj.__table__.columns:
        if x.name in dict:
            setattr(obj, x.name, dict[x.name])
    return obj

#########################################################################################

def check_500(any_func):
    u"""Декоратор для обнаружения каких-либо ошибок на сервере"""
    @wraps(any_func)
    def checking(data):
        try:
            return any_func(data)
        except:
            data['content'] = []
            data['status'] = '500'
            data['message'] = 'Произошла ошибка на сервере'
            logger.error(data['message'] + ' ' + data['status'])
            return data

    return checking

def check_token(any_func):
    u"""Декоратор для проверки токена клиента"""
    @wraps(any_func)
    def checking(data):
        try:
            tarantool_token = tarantool_space.select(data['token']).data[0]
            time_now = int(datetime.datetime.now().timestamp())
            last_time_token = time_now - tarantool_token[2]
            if last_time_token <= config['ttl']:
                if last_time_token <= config['ttl_update']:
                    return any_func(data)
                else:
                    tarantool_space.update(data['token'], [('=', 2, time_now)])
                    return any_func(data)
            else:
                tarantool_space.delete((data['token']))
                del data['token']
                data['content'] = []
                data['status'] = '403'
                data['message'] = 'Время вашего сеанса истекло!' + '\n' + 'Авторизируйтесь снова!'
        except:
            data['content'] = []
            data['status'] = '403'
            data['message'] = 'Вы не авторизованы, действие запрещено'
            logger.error(data['message'] + ' ' + data['status'])
        return data

    return checking

#########################################################################################

class Car(Base):
    u"""
    Класс транспортного средства

    Атрибуты\r\n
    ---\r\n
    Id (Integer): Уникальный идентификатор\r\n
    CompanyID (Integer): Уникальный идентификатор компании\r\n
    Location (String): Адрес расположения автомобиля\r\n
    Photos (String): Путь до фотографий\r\n
    RentCondition (String): Условия аренды\r\n
    Header (String): Заголовок объявления\r\n
    Driver (Boolean): Есть ли водитель у автомобиля\r\n
    status (Boolean): Статус автомобиля (скрыто или нет)\r\n
    CategoryID (Integer): Уникальный идентификатор категории\r\n
    CategoryVU (String): Категория ВУ автомобиля\r\n
    DateDel (Date): Дата удаления\r\n
    FixedRate (Numeric): Фиксированная комиссия\r\n
    Percent (Numeric): Процент комиссии\r\n
    Brand_and_name (String):Марка и модель автомобиля\r\n
    Transmission (Integer): Тип трансмиссии\r\n
    Engine (Integer): Тип двигателя\r\n
    Car_type (Integer): Тип кузова\r\n
    Drive (Integer): Тип привода\r\n
    Wheel_drive (Integer): Положение руля\r\n
    Year (Integer): Год выпуска\r\n
    Power (Integer): Мощность\r\n
    Price (Integer): Стоимость аренды\r\n
    ---
    """
    __tablename__ = 'Cars'

    Id = Column(Integer, primary_key=True, doc="Уникальный идентификатор")  # pk
    CompanyID = Column(Integer, ForeignKey('Company.Id'), nullable=False, doc="Уникальный идентификатор компании")  # fk
    Location = Column(String(250), nullable=False, doc="Адрес расположения автомобиля")
    Photos = Column(String, default='', doc="Путь до фотографий")
    RentCondition = Column(String, default='Описание условий аренды', doc="Условия аренды")
    Header = Column(String, nullable=False, doc="Заголовок объявления")
    Driver = Column(Boolean, nullable=False, doc="Есть ли водитель у автомобиля")
    status = Column(Boolean, nullable=True, doc="Статус автомобиля (скрыто или нет)")
    CategoryID = Column(Integer, ForeignKey('Category.Id'), nullable=False, doc="Уникальный идентификатор категории")  # fk
    CategoryVU = Column(String, nullable=False, doc="Категория ВУ автомобиля")
    DateDel = Column(Date, nullable=True, doc="Дата удаления")
    FixedRate = Column(Numeric, nullable=True, doc="Фиксированная комиссия")
    Percent = Column(Numeric, nullable=True, doc="Процент комиссии")

    car_company = relationship("Company", back_populates="company_cars", doc="Вспомогательное поле для создания связи с классом Company")
    car_category = relationship("Category", back_populates="category_cars", doc="Вспомогательное поле для создания связи с классом Category")
    car_contract = relationship("Contract", back_populates="contract_car", doc="Вспомогательное поле для создания связи с классом Contract")

    Brand_and_name = Column(String, nullable=False, doc="Марка и модель автомобиля")
    Transmission = Column(Integer, nullable=True, default=0, doc="Тип трансмиссии")
    Engine = Column(Integer, nullable=True, default=0, doc="Тип двигателя")
    Car_type = Column(Integer, nullable=True, default=0, doc="Тип кузова")
    Drive = Column(Integer, nullable=True, default=0, doc="Тип привода")
    Wheel_drive = Column(Integer, nullable=True, default=0, doc="Положение руля")
    Year = Column(Integer, nullable=False, doc="Год выпуска")
    Power = Column(Integer, nullable=False, doc="Мощность")
    Price = Column(Integer, nullable=False, doc="Стоимость аренды")

    @check_500
    @check_token
    def get_car(data):
        """
        Метод для получения информации об автомобиле\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией об автомобиле\r\n
        """
        car = session.query(Car).filter(Car.Id == int(data['content']['Id']), Car.DateDel == None).first()
        if car is not None:
            data['content'] = [object_to_dict(car)]
            data['status'] = '200'
            data['message'] = 'Просмотр ТС c id ' + str(data['content'][0]['Id'])
            logger.info(data['message'] + ' ' + data['status'])
        else:
            data['status'] = '404'
            data['message'] = 'ТС с id ' + str(data['content']['Id']) + ' не найдено'
            logger.error(str(data['message']) + ' ' + data['status'])
        return data

    @check_500
    @check_token
    def get_cars(data):
        """
        Метод для получения списка автомобилей определенной категории\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с данными автомобилей определенной категории\r\n
        """
        category = session.query(Category).get(int(data['content']['CategoryID']))
        if category == None:
            data['status'] = '404'
            data['message'] = 'Категории с id ' + str(data['content']['CategoryID']) + ' нет'
            logger.error(data['message'] + ' ' + data['status'])
        else:
            cars = category.category_cars
            new_cars = []  # [{} {} {}]
            for car in cars:
                if car.DateDel == None:
                    dict = object_to_dict(car)
                    new_cars.append(dict)
            if new_cars:
                data['status'] = '200'
                data['message'] = 'Просмотр списка ТС с категорией ' + str(data['content']['CategoryID'])
                logger.info(data['message'] + ' ' + data['status'])
                data['content'] = new_cars
            else:
                data['status'] = '404'
                data['message'] = 'ТС с категорией ' + str(data['content']['CategoryID']) + ' нет'
                logger.error(data['message'] + ' ' + data['status'])

        return data


class Person(Base):
    u"""
        Класс клиента

        Атрибуты\r\n
        ---\r\n
        Id (Integer): Уникальный идентификатор\r\n
        CompanyID (Integer): Уникальный идентификатор компании\r\n
        Name (String): Имя\r\n
        Surname (String): Фамилия\r\n
        Birthday (Date): Дата рождения\r\n
        Phone (String): Телефон\r\n
        Password (String): Пароль\r\n
        Token (String): Токен\r\n
        Email (String): Адрес электронной почты\r\n
        Position (Integer): Статус пользователя (Клиент, сотрудник, администратор)\r\n
        Comment (String): Комментарий к клиенту\r\n
        CategoryVuID (String): Категории ВУ\r\n
        NumVU (String): Номер ВУ\r\n
        DateDel (Date): Дата удаления\r\n
        ---
        """
    __tablename__ = 'Person'
    Id = Column(Integer, primary_key=True, doc="Уникальный идентификатор")  # pk
    CompanyID = Column(Integer, nullable=True, default=0, doc="Уникальный идентификатор компании")  # fk
    Name = Column(String, nullable=False, doc="Имя")
    Surname = Column(String, nullable=False, doc="Фамилия")
    Birthday = Column(Date, nullable=True, doc="Дата рождения")
    Phone = Column(String, nullable=False, doc="Телефон")
    Password = Column(String, nullable=False, doc="Пароль")
    Token = Column(String, nullable=False, doc="Токен")
    Email = Column(String, nullable=True, doc="Адрес электронной почты")
    Position = Column(Integer, nullable=True, doc="Статус пользователя (Клиент, сотрудник, администратор)")
    Comment = Column(String, nullable=True, doc="Комментарий к клиенту")
    CategoryVuID = Column(String, nullable=False, doc="Категории ВУ")
    NumVU = Column(String, nullable=False, doc="Номер ВУ")
    DateDel = Column(Date, nullable=True, doc="Дата удаления")

    client_contracts = relationship("Contract", back_populates="contract_client", doc="Вспомогательное поле для создания связи с классом Contract")
    favorites = relationship("Car", secondary="Favorites", doc="Вспомогательное поле для создания связи с классом Favorite")

    @check_500
    def sign_up(data):
        """
        Метод для регистрации клиента в системе\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией о регистрации или сообщение об ошибке\r\n
        """
        man = session.query(Person).filter(Person.Phone == data['content']['Phone'], Person.DateDel == None).first()
        if man is None:
            salted = hashlib.sha256(data['content']['Password'].encode() + salt.encode()).hexdigest()
            data['content']['Password'] = salted
            person = Person(**data['content'])
            person.Birthday = datetime.datetime.strptime(data['content']['Birthday'], "%d-%m-%Y")
            person.DateDel = None
            person.CompanyID = None
            person.Position = 0
            person.Comment = 'Я клиент'
            person.Token = uuid.uuid4().hex
            session.add(person)
            session.commit()
            tarantool_space.insert(
                (person.Token, person.Id, int(datetime.datetime.now().timestamp())))
            data = {}
            data['token'] = person.Token
            data['status'] = '200'
            data['content'] = []
            data['message'] = 'Вы успешно зарегистрировались! Ваш Id: ' + str(person.Id)
            logger.info(data['message'] + ' ' + data['status'])
        else:
            data['status'] = '500'
            data['message'] = 'Пользователь с таким телефоном уже зарегистрирован!'
            logger.error(data['message'] + ' ' + data['status'])
        return data

    @check_500
    def sign_in(data):
        """
        Метод для автоизации клиента в системе\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией об авторизации или сообщение об ошибке\r\n
        """
        salted = hashlib.sha256(data['content']['Password'].encode() + salt.encode()).hexdigest()
        man = session.query(Person).filter(Person.Phone == data['content']['Phone'], Person.Password == salted,
                                           Person.DateDel == None).first()
        if man is not None:
            data['content'] = []
            data['status'] = '200'
            data['token'] = man.Token = uuid.uuid4().hex
            session.add(man)
            session.commit()
            tarantool_space.insert(
                (man.Token, man.Id, int(datetime.datetime.now().timestamp())))
            data['message'] = 'Вы авторизовались. ' + 'Ваш id: ' + str(man.Id)
            logger.info(data['message'] + ' ' + data['status'])
        else:
            data['status'] = '404'
            data['message'] = 'Неверный телефон или пароль. Попробуйте снова. '
            logger.error(str(data['message']) + ' ' + data['status'])

        return data

    @check_500
    @check_token
    def get_client(data):
        """
        Метод для получении личных данных клиента\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с личной информацией клиента или сообщение об ошибке\r\n
        """
        man = session.query(Person).filter(Person.Token == data['token'], Person.DateDel == None).first()
        data['content'] = [object_to_dict(man)]
        del (data['content'][0]['Password'])
        del (data['content'][0]['Token'])
        data['token'] = man.Token
        data['status'] = '200'
        data['message'] = 'Данные клиента с id ' + str(man.Id)
        logger.info(data['message'] + ' ' + data['status'])

        return data

    @check_500
    @check_token
    def del_client(data):
        """
        Метод для удаления клиента из системы\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией об удалении или сообщение об ошибке\r\n
        """
        man = session.query(Person).filter(Person.Token == data['token'], Person.DateDel == None).first()
        man.DateDel = datetime.date.today()
        session.add(man)
        session.commit()
        data['content'] = []
        data['status'] = '200'
        data['message'] = 'Аккаунт с id ' + str(man.Id) + ' удален'
        logger.info(data['message'] + ' ' + data['status'])

        return data

    @check_500
    @check_token
    def edit_pass(data):
        """
        Метод для смены пароля клиента\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией о смене пароля или сообщение об ошибке\r\n
        """
        man = session.query(Person).filter(Person.Token == data['token'], Person.DateDel == None).first()
        salted = hashlib.sha256(data['content']['Password'].encode() + salt.encode()).hexdigest()
        man.Password = salted
        session.add(man)
        session.commit()
        data['content'] = []
        data['status'] = '200'
        data['token'] = man.Token
        data['message'] = 'Пароль изменен! Ваш Id: ' + str(man.Id)
        logger.info(data['message'] + ' ' + data['status'])

        return data

    @check_500
    @check_token
    def edit_client(data):
        """
        Метод для редактирования личных данных клиента\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией об успешном редактировании или сообщение об ошибке\r\n
        """
        man = session.query(Person).filter(Person.Token == data['token'], Person.DateDel == None).first()
        man = dict_to_object(man, data['content'])
        man.Birthday = datetime.datetime.strptime(data['content']['Birthday'], "%d-%m-%Y")
        session.add(man)
        session.commit()
        data['content'] = []
        data['token'] = man.Token
        data['status'] = '200'
        data['message'] = 'Данные вашего аккаунта измнены! Ваш Id: ' + str(man.Id)
        logger.info(data['message'] + ' ' + data['status'])

        return data

    @check_500
    @check_token
    def log_out(data):
        """
        Метод для выхода клиента из системы\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией о выходе из системы или сообщение об ошибке\r\n
        """
        tarantool_space.delete((data['token']))
        data = {}
        data['content'] = []
        data['status'] = '200'
        data['message'] = 'Вы вышли из аккаунта!'
        logger.info(data['message'] + ' ' + data['status'])

        return data


class Company(Base):
    u"""
        Класс компании

        Атрибуты\r\n
        ---\r\n
        Id (Integer): Уникальный идентификатор\r\n
        Name (String): Название компании\r\n
        Phone (String): Телефон\r\n
        Email (String): Адрес электронной почты\r\n
        Note (String): Комментарий к компании\r\n
        DateDel (Date): Дата удаления\r\n
        FIOContact (String): ФИО представителя компании\r\n
        ContactPhone (String): Телефон представителя компании\r\n
        ContactEmail (String): Адрес электронной почты представителя компании\r\n
        ---
    """
    __tablename__ = 'Company'
    Id = Column(Integer, primary_key=True, doc="Уникальный идентификатор")  # pk
    Name = Column(String, nullable=False, doc="Название компании")
    Phone = Column(String, nullable=False, doc="Телефон")
    Email = Column(String, nullable=True, doc="Адрес электронной почты")
    Note = Column(String, nullable=True, doc="Комментарий к компании")
    DateDel = Column(Date, nullable=True, doc="Дата удаления")
    FIOContact = Column(String, nullable=False, doc="ФИО представителя компании")
    ContactPhone = Column(String, nullable=False, doc="Телефон представителя компании")
    ContactEmail = Column(String, nullable=True, doc="Адрес электронной почты представителя компании")
    company_cars = relationship("Car", back_populates="car_company", doc="Вспомогательное поле для создания связи с классом Car")


class Category(Base):
    u"""
        Класс категории

        Атрибуты\r\n
        ---\r\n
        Id (Integer): Уникальный идентификатор\r\n
        NameCat (String): Название категории\r\n
        Icon (String): Путь до иконки\r\n
        DateDel (Date): Дата удаления\r\n
        ---
    """
    __tablename__ = 'Category'
    Id = Column(Integer, primary_key=True, doc="Уникальный идентификатор")  # pk
    NameCat = Column(String, nullable=False, doc="Название категории")
    Icon = Column(String, nullable=True, doc="Путь до иконки")
    DateDel = Column(Date, nullable=True, doc="Дата удаления")
    category_cars = relationship("Car", back_populates="car_category", doc="Вспомогательное поле для создания связи с классом Car")


class Contract(Base):
    u"""
        Класс договора

        Атрибуты\r\n
        ---\r\n
        Id (Integer): Уникальный идентификатор\r\n
        ClientId (Integer): Уникальный идентификатор клиента\r\n
        CarId (Integer): Уникальный идентификатор автомобиля\r\n
        DateStartContract (Date): Дата начала аренды\r\n
        DateEndContract (Date): Дата окончания аренды\r\n
        Driver (Boolean): Требуется ли водитель для аренды\r\n
        Note (String): Комментарий к заявке\r\n
        Status (Integer): Статус заявки (Активна, завершена, отменена)\r\n
        Comission (Numeric): Комиссия с заявки\r\n
        Cost (Integer): Стоимость аренды\r\n
        DateDel (Date): Дата удаления\r\n
        ---
    """
    __tablename__ = 'Contract'
    Id = Column(Integer, primary_key=True, doc="Уникальный идентификатор")  # pk
    ClientId = Column(Integer, ForeignKey('Person.Id'), nullable=False, doc="Уникальный идентификатор клиента")  # fk
    CarId = Column(Integer, ForeignKey('Cars.Id'), nullable=False, doc="Уникальный идентификатор автомобиля")  # fk
    DateStartContract = Column(Date, nullable=False, doc="Дата начала аренды")
    DateEndContract = Column(Date, nullable=False, doc="Дата окончания аренды")
    Driver = Column(Boolean, nullable=False, doc="Требуется ли водитель для аренды")
    Note = Column(String, nullable=True, doc="Комментарий к заявке")
    Status = Column(Integer, nullable=False, doc="Статус заявки (Активна, завершена, отменена)")
    Comission = Column(Numeric, nullable=False, doc="Комиссия с заявки")
    Cost = Column(Integer, nullable=False, doc="Стоимость аренды")
    DateDel = Column(Date, nullable=True, doc="Дата удаления")
    contract_client = relationship("Person", back_populates="client_contracts", doc="Вспомогательное поле для создания связи с классом Person")
    contract_car = relationship("Car", back_populates="car_contract", doc="Вспомогательное поле для создания связи с классом Car")

    @check_500
    @check_token
    def add_order(data):
        """
        Метод для для добавления договора\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией о создании договора или сообщение об ошибке\r\n
        """
        man = session.query(Person).filter(Person.Token == data['token'], Person.DateDel == None).first()
        car = session.query(Car).filter(Car.Id == data['content']['CarId'], Car.DateDel == None).first()
        if car is not None:
            start = datetime.datetime.strptime(data['content']['DateStartContract'], "%d-%m-%Y")
            end = datetime.datetime.strptime(data['content']['DateEndContract'], "%d-%m-%Y")
            rez = (end - start).days
            cost = rez * car.Price
            car_per = car.Percent
            car_fix = car.FixedRate
            per1 = car_per * decimal.Decimal(0.01)
            per2 = round((per1 * decimal.Decimal(cost)) + car_fix, 2)

            contract = Contract(**data['content'])
            contract.DateStartContract = datetime.datetime.strptime(data['content']['DateStartContract'],
                                                                    "%d-%m-%Y")
            contract.DateEndContract = datetime.datetime.strptime(data['content']['DateEndContract'], "%d-%m-%Y")
            contract.ClientId = man.Id
            contract.CarId = car.Id
            contract.Cost = cost
            contract.Comission = per2
            contract.Driver = False
            contract.Status = 0
            session.add(contract)
            session.commit()
            data['content'] = []
            data['status'] = '200'
            data['message'] = 'Заявка добавлена! Id заявки: ' + str(contract.Id)
            logger.info(data['message'] + ' ' + data['status'])
        else:
            data['status'] = '500'
            data['message'] = 'Автомобиль не найден!'
            logger.error(data['message'] + ' ' + data['status'])

        return data

    @check_500
    @check_token
    def get_order(data):
        """
        Метод для для получение информации договора\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией договоре или сообщение об ошибке\r\n
        """
        contract = session.query(Contract).filter(Contract.Id == int(data['content']['Id']),
                                                  Contract.DateDel == None).first()
        man = session.query(Person).filter(Person.Token == data['token'], Person.DateDel == None).first()
        l = list(filter(lambda x: x.Id == int(data['content']['Id']), man.client_contracts))
        contract = l[0] if l != [] else None
        if contract is not None:
            data['content'] = [object_to_dict(contract)]
            c = contract.contract_car.Id
            data['content'][0]['CarId'] = contract.contract_car.Brand_and_name + ': id ' + str(
                contract.contract_car.Id)
            data['status'] = '200'
            data['message'] = 'Просмотр заявки c id ' + str(data['content'][0]['Id'])
            logger.info(data['message'] + ' ' + data['status'])
        else:
            data['status'] = '404'
            data['message'] = 'Заявка с id ' + str(data['content']['Id']) + ' не найдена'
            logger.error(str(data['message']) + ' ' + data['status'])

        return data

    @check_500
    @check_token
    def get_orders(data):
        """
        Метод для для получения списка договоров\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь со списком договоров или сообщение об ошибке\r\n
        """
        man = session.query(Person).filter(Person.Token == data['token'], Person.DateDel == None).first()
        list_contract = list(man.client_contracts)
        contracts = []
        for o in list_contract:
            object = object_to_dict(o)
            c = o.contract_car
            object['CarId'] = c.Brand_and_name + ': id ' + str(c.Id)
            contracts.append(object)
        if contracts:
            data['content'] = contracts
            data['status'] = '200'
            data['message'] = 'Просмотр заявок клиента с id ' + str(man.Id)
            logger.info(data['message'] + ' ' + data['status'])
        else:
            data['status'] = '404'
            data['message'] = 'Заявок у клиента с id ' + str(man.Id) + ' нет!'
            logger.error(str(data['message']) + ' ' + data['status'])

        return data


class Favorite(Base):
    u"""
        Класс договора

        Атрибуты\r\n
        ---\r\n
        Id (Integer): Уникальный идентификатор\r\n
        ClientId (Integer): Уникальный идентификатор клиента\r\n
        CarId (Integer): Уникальный идентификатор автомобиля\r\n
        Date_add (Date): Дата добавления в избранное\r\n
        DateDel (Date): Дата удаления\r\n
        ---
    """
    __tablename__ = 'Favorites'
    Id = Column(Integer, primary_key=True, doc="Уникальный идентификатор")  # pk
    ClientId = Column(Integer, ForeignKey('Person.Id'), nullable=False, doc="Уникальный идентификатор клиента")  # fk
    CarId = Column(Integer, ForeignKey('Cars.Id'), nullable=False, doc="Уникальный идентификатор автомобиля")  # fk
    Date_add = Column(Date, nullable=True, doc="Дата добавления в избранное")
    DateDel = Column(Date, nullable=True, doc="Дата удаления")

    @check_500
    @check_token
    def add_favorite(data):
        """
        Метод для для добавления автомобиля в избранное клиента\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией о добавлении автомобиля в избранное или сообщение об ошибке\r\n
        """
        man = session.query(Person).filter(Person.Token == data['token'], Person.DateDel == None).first()
        car = session.query(Car).filter(Car.Id == data['content']['CarId'], Car.DateDel == None).first()
        if car is not None:
            if car not in man.favorites:
                fav = Favorite()
                fav.CarId = car.Id
                fav.ClientId = man.Id
                fav.Date_add = datetime.date.today()
                session.add(fav)
                session.commit()
                data['content'] = []
                data['status'] = '200'
                data['message'] = 'Авто добавлено в избранное! Id авто: ' + str(car.Id)
                logger.info(data['message'] + ' ' + data['status'])
            else:
                data['status'] = '500'
                data['message'] = 'Авто с id ' + str(car.Id) + ' уже добавлено в избранное!'
                logger.error(data['message'] + ' ' + data['status'])
        else:
            data['status'] = '500'
            data['message'] = 'Автомобиль не найден!'
            logger.error(data['message'] + ' ' + data['status'])

        return data

    @check_500
    @check_token
    def del_favorite(data):
        """
        Метод для для удаления автомобиля из списка избранного клиента\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь с информацией об удалении автомобиля из списка избранного клиента или сообщение об ошибке\r\n
        """
        man = session.query(Person).filter(Person.Token == data['token'], Person.DateDel == None).first()
        fav = session.query(Favorite).filter(Favorite.ClientId == man.Id,
                                             Favorite.CarId == data['content']['CarId']).first()
        if fav is not None:
            session.delete(fav)
            session.commit()
            data['content'] = []
            data['status'] = '200'
            data['message'] = 'ТС с id ' + str(fav.CarId) + ' удалено из избранного'
            logger.info(data['message'] + ' ' + data['status'])
        else:
            data['status'] = '404'
            data['message'] = 'ТС с id ' + str(data['content']['CarId']) + ' не найдено в избранном'
            logger.error(str(data['message']) + ' ' + data['status'])

        return data

    @check_500
    @check_token
    def get_favorites(data):
        """
        Метод для для получения списка автомобилей из избранного\r\n
        Параметры:\r\n
            data: словарь с информацией полученной от клиента\r\n
        Возвращаемое значение:\r\n
            data: словарь со спиком автомобилей или сообщение об ошибке\r\n
        """
        man = session.query(Person).filter(Person.Token == data['token'], Person.DateDel == None).first()
        list_favorites = list(man.favorites)
        favorites = []
        for o in list_favorites:
            object = {}
            object['CarId'] = o.Brand_and_name + ': id ' + str(o.Id)
            favorites.append(object)
        if favorites:
            data['content'] = favorites
            data['status'] = '200'
            data['message'] = 'Просмотр списка избранного клиента с id ' + str(man.Id)
            logger.info(data['message'] + ' ' + data['status'])
        else:
            data['status'] = '404'
            data['message'] = 'Список избранного у клиента с id ' + str(man.Id) + ' пуст!'
            logger.error(str(data['message']) + ' ' + data['status'])

        return data


###########################################################################################################
client_data = {}
# удаление всех записей в Tarantool (очистка перед каждым запуском, в будущем можно очищать раз в 24 часа)
connection_tarantool.call('box.space.user_token:truncate', ())


def server_thread():  # pragma: no cover
    """
    Метод для запуска сервера в потоке\r\n
    Параметры:\r\n
        connection: данные о соединении клиента\r\n
        address: адресс клиента в сети\r\n
    """
    ###########################################################################################################
    cars_dict = {
        'get_cars': Car.get_cars,
        'get_car': Car.get_car
    }
    person_dict = {
        'sign_up': Person.sign_up,
        'sign_in': Person.sign_in,
        'get_client': Person.get_client,
        'del_client': Person.del_client,
        'edit_pass': Person.edit_pass,
        'edit_client': Person.edit_client,
        'log_out': Person.log_out,
        'add_favorite': Favorite.add_favorite,
        'del_favorite': Favorite.del_favorite,
        'get_favorites': Favorite.get_favorites
    }
    contract_dict = {
        'add_order': Contract.add_order,
        'get_order': Contract.get_order,
        'get_orders': Contract.get_orders,
    }

    while True:
        def callback(ch, method,  props, body):
            client_data = json.loads(body)
            new_client_dict = client_data
            if client_data['endpoint'] == 'cars':
                q = client_data['action']
                new_client_dict = cars_dict.get(q)(client_data)
            if client_data['endpoint'] == 'clients':
                q = client_data['action']
                new_client_dict = person_dict.get(q)(client_data)
            if client_data['endpoint'] == 'orders':
                q = client_data['action']
                new_client_dict = contract_dict.get(q)(client_data)
            client_data = {}
            new_client_dict = (json.dumps(new_client_dict, ensure_ascii=False, default=str))
            channel.basic_publish(exchange='', routing_key=props.reply_to, properties=pika.BasicProperties(correlation_id = props.correlation_id), body=new_client_dict)
        channel.basic_consume(queue='server_queue', on_message_callback=callback, auto_ack=True)
        channel.start_consuming()


def launch_server():  # pragma: no cover
    """Метод для инициализации сервера и ожидания подключения клиента """
    logger.info('****** RabbitMq ******')
    logger.info('Срвер запущен по адресу ' + config['address'] + ':' + str(config['port']))
    server_thread()


# Base.metadata.create_all(db_engine)
launch_server()

