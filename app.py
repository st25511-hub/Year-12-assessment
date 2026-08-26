from flask import Flask, render_template, request
import json
import random
import string

app = Flask(__name__)

DATA_FILE = "data/events.json"

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
    code = "".join(random.choices(characters, k=6))
    return f"EVT-{code}"


def validate_quantity(quantity, available):
    """Check whether the ticket quantity is valid."""
    if quantity < 1:
        return False, "You must book at least one ticket."

    if quantity > available:
        return False, f"Only {available} tickets are available."

    return True, ""


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


if __name__ == "__main__":
    app.run(debug=True)