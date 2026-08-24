from flask import Flask, render_template, request, redirect, url_for
import json
import os
import random
import string

app = Flask(__name__)

DATA_FILE = "data/events.json"


def load_events():
    """Load event information from the JSON file."""
    with open(DATA_FILE, "r") as file:
        return json.load(file)


def save_events(events):
    """Save updated event information to the JSON file."""
    with open(DATA_FILE, "w") as file:
        json.dump(events, file, indent=4)


def calculate_total(price, quantity):
    """Calculate the total cost of a booking."""
    return price * quantity


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

        total = calculate_total(event["price"], quantity)

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
            "total": total
        }

        return render_template(
            "confirmation.html",
            booking=booking
        )

    return render_template(
        "booking.html",
        event=event,
        event_name=event_name
    )


if __name__ == "__main__":
    app.run(debug=True)