from flask import Flask, render_template, request
import json
import random
import string
import sqlite3

app = Flask(__name__)

DATA_FILE = "data/events.json"
DATABASE_FILE = "data/bookings.db"

TICKET_PRICES = {
    "Student": 0.85,
    "Staff": 1.00,
    "Adult": 1.25,
    "Child": 0.65
}


def load_events():
    """Load event information from the JSON file."""
    with open(DATA_FILE, "r") as file:
        return json.load(file)


def save_events(events):
    """Save updated event information to the JSON file."""
    with open(DATA_FILE, "w") as file:
        json.dump(events, file, indent=4)


def calculate_total(price, quantity, ticket_type):
    """Calculate the total cost of a booking."""
    final_price = price * TICKET_PRICES[ticket_type]
    return final_price * quantity


def get_ticket_price(price, ticket_type):
    """Calculate the price of one ticket."""
    return price * TICKET_PRICES[ticket_type]


def generate_reference():
    """Generate a unique booking reference."""

    characters = string.ascii_uppercase + string.digits

    while True:
        code = "".join(random.choices(characters, k=6))
        reference = f"EVT-{code}"

        connection = sqlite3.connect(DATABASE_FILE)

        existing = connection.execute(
            "SELECT 1 FROM bookings WHERE reference = ?",
            (reference,)
        ).fetchone()

        connection.close()

        if existing is None:
            return reference


def validate_quantity(quantity, available):
    """Check whether the ticket quantity is valid."""
    if quantity < 1:
        return False, "You must book at least one ticket."

    if quantity > available:
        return False, f"Only {available} tickets are available."

    return True, ""


def initialise_database():
    """Create the bookings database if it does not exist."""

    connection = sqlite3.connect(DATABASE_FILE)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            event TEXT NOT NULL,
            ticket_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            ticket_price REAL NOT NULL,
            total REAL NOT NULL,
            booking_date TEXT DEFAULT CURRENT_TIMESTAMP,
            cancelled INTEGER NOT NULL DEFAULT 0
        )
    """)

    columns = [
        row[1] for row in connection.execute(
            "PRAGMA table_info(bookings)"
        ).fetchall()
    ]

    if "cancelled" not in columns:
        connection.execute("""
            ALTER TABLE bookings
            ADD COLUMN cancelled INTEGER NOT NULL DEFAULT 0
        """)

    connection.commit()
    connection.close()


def save_booking(booking):
    """Save customer booking information into the database."""

    connection = sqlite3.connect(DATABASE_FILE)

    connection.execute("""
        INSERT INTO bookings (
            reference,
            name,
            email,
            event,
            ticket_type,
            quantity,
            ticket_price,
            total
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        booking["reference"],
        booking["name"],
        booking["email"],
        booking["event"],
        booking["ticket_type"],
        booking["quantity"],
        booking["ticket_price"],
        booking["total"]
    ))

    connection.commit()
    connection.close()


@app.route("/")
def index():
    """Display all available school events."""
    events = load_events()
    return render_template("index.html", events=events)


@app.route("/book/<event_name>", methods=["GET", "POST"])
def book(event_name):
    """Display and process the booking form."""
    events = load_events()

    if event_name not in events:
        return "Event not found", 404

    event = events[event_name]

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        ticket_type = request.form.get("ticket_type", "")
        quantity_text = request.form.get("quantity", "")

        if not name or not email:
            error = "Please enter your name and email."
            return render_template(
                "booking.html",
                event=event,
                event_name=event_name,
                error=error
            )

        if ticket_type not in TICKET_PRICES:
            error = "Please select a valid ticket type."
            return render_template(
                "booking.html",
                event=event,
                event_name=event_name,
                error=error
            )

        try:
            quantity = int(quantity_text)
        except ValueError:
            error = "Please enter a valid whole number."
            return render_template(
                "booking.html",
                event=event,
                event_name=event_name,
                error=error
            )

        valid, error = validate_quantity(
            quantity,
            event["available"]
        )

        if not valid:
            return render_template(
                "booking.html",
                event=event,
                event_name=event_name,
                error=error
            )

        ticket_price = get_ticket_price(
            event["price"],
            ticket_type
        )

        total = calculate_total(
            event["price"],
            quantity,
            ticket_type
        )

        event["available"] -= quantity
        save_events(events)

        reference = generate_reference()

        booking = {
            "reference": reference,
            "name": name,
            "email": email,
            "event": event_name,
            "ticket_type": ticket_type,
            "quantity": quantity,
            "ticket_price": ticket_price,
            "total": total
        }

        save_booking(booking)

        return render_template(
            "confirmation.html",
            booking=booking
        )

    return render_template(
        "booking.html",
        event=event,
        event_name=event_name,
        ticket_prices=TICKET_PRICES
    )


@app.route("/cancel", methods=["GET", "POST"])
def cancel_booking():
    """Find and cancel an existing booking."""

    if request.method == "POST":
        reference = request.form.get("reference", "").strip().upper()
        email = request.form.get("email", "").strip()

        connection = sqlite3.connect(DATABASE_FILE)
        connection.row_factory = sqlite3.Row

        booking = connection.execute("""
            SELECT * FROM bookings
            WHERE reference = ? AND email = ?
        """, (reference, email)).fetchone()

        if booking is None:
            connection.close()
            return render_template(
                "cancel.html",
                error="No booking was found with those details."
            )

        if booking["cancelled"] == 1:
            connection.close()
            return render_template(
                "cancel.html",
                error="This booking has already been cancelled."
            )

        events = load_events()
        event_name = booking["event"]

        if event_name not in events:
            connection.close()
            return render_template(
                "cancel.html",
                error="The event could not be found."
            )

        cursor = connection.execute("""
            UPDATE bookings
            SET cancelled = 1
            WHERE reference = ? AND cancelled = 0
        """, (reference,))

        if cursor.rowcount != 1:
            connection.close()
            return render_template(
                "cancel.html",
                error="This booking has already been cancelled."
            )

        connection.commit()
        connection.close()

        events[event_name]["available"] += booking["quantity"]
        save_events(events)

        return render_template(
            "cancellation_confirmation.html",
            booking=booking
        )

    return render_template("cancel.html")

initialise_database()

if __name__ == "__main__":
    app.run(debug=True)