from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from typing import List
import unittest

class CarType(Enum):
    SEDAN = "sedan"
    SUV = "suv"
    VAN = "van"

@dataclass
class ReservationPeriod:
    start_date: datetime
    end_date: datetime

    def conflicts_with(self, other: "ReservationPeriod") -> bool:
        return not (self.end_date <= other.start_date or self.start_date >= other.end_date)

@dataclass
class Car:
    car_id: int      
    car_type: CarType 

@dataclass
class Reservation:
    car_id: int           
    period: ReservationPeriod  

class NoAvailableCarsError(Exception):
    pass

class CarInventory(ABC):
    @abstractmethod
    def add_car(self, car: Car):
        pass

    @abstractmethod
    def check_availability(self, car_type: CarType, start_date: datetime, days: int) -> bool:
        pass

    @abstractmethod
    def reserve_car(self, car_type: CarType, start_date: datetime, days: int) -> Reservation:
        pass

class InMemoryCarInventory(CarInventory):
    def __init__(self):
        self.cars: List[Car] = []
        self.reservations: dict[int, List[Reservation]] = {}

    def add_car(self, car: Car):
        self.cars.append(car)

    def check_availability(self, car_type: CarType, start_date: datetime, days: int) -> bool:
        available_cars = [
            car for car in self.cars 
            if car.car_type == car_type and not self.is_car_reserved(car.car_id, start_date, days)
        ]
        return len(available_cars) > 0

    def _is_period_conflicting(self, start: datetime, end: datetime, res: Reservation) -> bool:
        return not (res.period.end_date <= start or res.period.start_date >= end)

    def is_car_reserved(self, car_id: int, start_date: datetime, days: int) -> bool:
        period = ReservationPeriod(start_date, start_date + timedelta(days=days))
        return any(period.conflicts_with(res.period) for res in self.reservations.get(car_id, []))

    def reserve_car(self, car_type: CarType, start_date: datetime, days: int) -> Reservation:
        if days <= 0:
            raise ValueError("The number of reservation days must be greater than zero.")

        if start_date < datetime.now():
            raise ValueError("The reservation start date cannot be in the past.")

        available_cars = [
            car for car in self.cars 
            if car.car_type == car_type and not self.is_car_reserved(car.car_id, start_date, days)
        ]
        
        if available_cars:
            car_to_reserve = available_cars[0]
            period = ReservationPeriod(start_date, start_date + timedelta(days=days))
            reservation = Reservation(car_id=car_to_reserve.car_id, period=period)
            self.reservations.setdefault(car_to_reserve.car_id, []).append(reservation)
            return reservation
        else:
            raise NoAvailableCarsError("No cars available for the requested type and dates")


class CarRentalSystem:
    def __init__(self, inventory: CarInventory):
        self.inventory = inventory

    def add_car(self, car_id: int, car_type: CarType):
        car = Car(car_id=car_id, car_type=car_type)
        self.inventory.add_car(car)

    def reserve_car(self, car_type: CarType, start_date: datetime, days: int) -> Reservation:
        return self.inventory.reserve_car(car_type, start_date, days)

    def check_availability(self, car_type: CarType, start_date: datetime, days: int) -> bool:
        return self.inventory.check_availability(car_type, start_date, days)

class TestCarRentalSystem(unittest.TestCase):
    def setUp(self):
        self.inventory = InMemoryCarInventory()
        self.rental_system = CarRentalSystem(self.inventory)
        self.rental_system.add_car(1, CarType.SEDAN)
        self.rental_system.add_car(2, CarType.SEDAN)
        self.rental_system.add_car(3, CarType.SUV)
        self.rental_system.add_car(4, CarType.VAN)

    def test_reserve_car_success(self):
        start_date = datetime.now() + timedelta(days=1)
        reservation = self.rental_system.reserve_car(CarType.SEDAN, start_date, 200)
        self.assertIn(reservation, self.inventory.reservations[reservation.car_id])

    def test_check_availability(self):
        start_date = datetime.now() + timedelta(days=1)
        self.assertTrue(self.rental_system.check_availability(CarType.SUV, start_date, 3))

    def test_reserve_car_no_availability(self):
        start_date = datetime.now() + timedelta(days=1)
        self.rental_system.reserve_car(CarType.VAN, start_date, 3)
        with self.assertRaises(NoAvailableCarsError):
            self.rental_system.reserve_car(CarType.VAN, start_date, 3)

    def test_minimum_days_reservation(self):
        start_date = datetime.now() + timedelta(days=1)
        reservation = self.rental_system.reserve_car(CarType.SEDAN, start_date, 1)
        self.assertIn(reservation, self.inventory.reservations[reservation.car_id])

    def test_maximum_days_reservation(self):
        start_date = datetime.now() + timedelta(days=1)
        reservation = self.rental_system.reserve_car(CarType.SUV, start_date, 365)
        self.assertIn(reservation, self.inventory.reservations[reservation.car_id])

    def test_reservation_with_minimal_availability(self):
        start_date = datetime.now() + timedelta(days=1)
        reservation = self.rental_system.reserve_car(CarType.SUV, start_date, 5)
        self.assertIn(reservation, self.inventory.reservations[reservation.car_id])

        with self.assertRaises(NoAvailableCarsError):
            self.rental_system.reserve_car(CarType.SUV, start_date, 5)

    def test_multiple_reservations(self):
        start_date = datetime.now() + timedelta(days=1)
        reservation_1 = self.rental_system.reserve_car(CarType.SEDAN, start_date, 3)
        reservation_2 = self.rental_system.reserve_car(CarType.SEDAN, start_date, 3)
        self.assertIn(reservation_1, self.inventory.reservations[reservation_1.car_id])
        self.assertIn(reservation_2, self.inventory.reservations[reservation_2.car_id])

    def test_reservation_overlap(self):
        start_date = datetime.now() + timedelta(days=1)
        self.rental_system.reserve_car(CarType.SUV, start_date, 3)
        with self.assertRaises(NoAvailableCarsError):
            self.rental_system.reserve_car(CarType.SUV, start_date, 3)

    def test_non_overlapping_reservations(self):
        start_date_1 = datetime.now() + timedelta(days=1)
        start_date_2 = datetime.now() + timedelta(days=5)
        reservation_1 = self.rental_system.reserve_car(CarType.SUV, start_date_1, 3)
        reservation_2 = self.rental_system.reserve_car(CarType.SUV, start_date_2, 3)
        self.assertIn(reservation_1, self.inventory.reservations[reservation_1.car_id])
        self.assertIn(reservation_2, self.inventory.reservations[reservation_2.car_id])

    def test_long_term_reservation(self):
        start_date = datetime.now() + timedelta(days=1)
        reservation = self.rental_system.reserve_car(CarType.SUV, start_date, 14)
        self.assertIn(reservation, self.inventory.reservations[reservation.car_id])

    def test_large_number_of_reservations(self):
        for i in range(1000, 1050):
            self.rental_system.add_car(i, CarType.SEDAN)
        
        start_date = datetime.now() + timedelta(days=1)
        for i in range(50):
            reservation = self.rental_system.reserve_car(CarType.SEDAN, start_date, 3)
            self.assertIn(reservation, self.inventory.reservations[reservation.car_id])

    def test_reserve_past_date(self):
        start_date = datetime.now() - timedelta(days=1) 
        with self.assertRaises(ValueError):
            self.rental_system.reserve_car(CarType.SUV, start_date, 3)

if __name__ == "__main__":
    unittest.main()
