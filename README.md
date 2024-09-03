# BusTicketX

BusTicketX is a Django-based web application for bus ticket reservations. The app allows users to search for buses, book tickets, manage bookings, and make payments. It offers a user-friendly interface similar to redBus but with unique features and a custom design.

## Features

- **List of Available Buses**: Search and view buses based on departure and arrival times.
- **Bus Operators**: View names of bus operators providing services.
- **Bus Types**: Information about bus types (e.g., sleeper, semi-sleeper, AC, non-AC).
- **Seats Availability**: Check the number of available seats.
- **Fares**: View ticket prices.
- **Bus Ratings and Reviews**: Read ratings and reviews from previous passengers.
- **Travel Duration**: Estimated journey duration.
- **Filters**: Filter search results by bus type, operator, departure times, and fare ranges.
- **Booking Management**: View and manage bookings, download tickets, and send SMS notifications.
- **Payment Integration**: Make payments through mobile money (MTN and Vodafone MoMo) and bank options using Paystack.

## Prerequisites

- Python 3.x
- Django
- VS Code
- Paystack Account
- Africastalking Account

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/Manager450/FinalYearProject.git
    cd FinalYearProject
    ```

2. **Create and activate the virtual environment:**

    ```bash
    python -m venv djangoenv
    source djangoenv/bin/activate  # On Windows use: djangoenv\Scripts\activate
    ```

3. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables:**

    Create a `.env` file in the root directory and add the following:

    ```env
    SECRET_KEY=your_secret_key
    DEBUG=True
    ALLOWED_HOSTS=localhost,127.0.0.1
    PAYSTACK_SECRET_KEY=your_paystack_secret_key
    ```

5. **Run migrations:**

    ```bash
    python manage.py migrate
    ```

6. **Start the development server:**

    ```bash
    python manage.py runserver
    ```

    Open your browser and go to `http://127.0.0.1:8000/` to see the app in action.

## Usage

- **Home**: Start your journey by finding available buses.
- **Find Bus**: Search for buses based on your source, destination, and travel date.
- **My Bookings**: View and manage your bookings.
- **Register/Login**: Create an account or log in to manage bookings.
- **Settings**: Update your profile and account settings.
- **Help/FAQs**: Access support and frequently asked questions.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/your-feature`).
3. Make your changes.
4. Commit your changes (`git commit -am 'Add new feature'`).
5. Push to the branch (`git push origin feature/your-feature`).
6. Create a new Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Django](https://www.djangoproject.com/)
- [Paystack](https://paystack.com/)
- [VS Code](https://code.visualstudio.com/)
- [redBus](https://www.redbus.com/)
- [Africastalking](https://www.africastalking.com/)