import requests
import bs4
from typing import List, Sequence, Tuple
from dataclasses import dataclass
import datetime as dt
import os

URL = "https://www.iclub.be/register.asp?ClubID=28&action2=Planning&LG=FR"


@dataclass
class Slot:
    start_datetime: dt.datetime
    end_datetime: dt.datetime
    remaining_places: int


def parse_date(date_str: str) -> dt.date:
    date_str = date_str.split()[1]
    return dt.datetime.strptime(date_str, "%d/%m/%Y").date()


def get_available_places(place_span: bs4.Tag) -> int:
    if "place-complet" in place_span.attrs["class"]:
        return 0

    return int(place_span.text.strip().split(" ")[0])


def get_slot_times(hours_span: bs4.Tag) -> Tuple[dt.time, ...]:
    times_str = hours_span.text.strip().split(" - ")
    return tuple((dt.time.fromisoformat(t) for t in times_str))


def split_spans_by_date(dates: Sequence[str], spans: Sequence[bs4.Tag]) -> List[Slot]:
    """
    Groups slot HTML spans by date and produces the corresponding Slot list.

    Dates and slot spans appear on the same level in the HTML code. This function links the slot hours with
    the correct date and produces the Slot objects.

    :param dates: List of dates in the planning, in order of apparition in the planning page.
    :param spans: List of slot HTML spans, in order of apparition in the planning page.
    :return: A list of Slot objects corresponding to each slot in the planning.
    """
    slots: List[Slot] = []

    dates_iter = (parse_date(d) for d in dates)
    current_date = next(dates_iter)

    for span in spans:
        elems = span.find_all("span")
        hours = get_slot_times(elems[1])
        places = get_available_places(elems[-1])

        if slots and slots[-1].start_datetime.time() > hours[0]:
            current_date = next(dates_iter)

        slot = Slot(
            start_datetime=dt.datetime.combine(current_date, hours[0]),
            end_datetime=dt.datetime.combine(current_date, hours[1]),
            remaining_places=places,
        )

        slots.append(slot)

    return slots


def parse_planning_html(text: str) -> Sequence[Slot]:
    """
    Parses the HTML content of the Calypso planning page and returns the list of slots.
    :return: The list of slots, available or not.
    """
    soup = bs4.BeautifulSoup(text, "html.parser")
    dates = [elem.text for elem in soup.select("div[class='change-date']")]
    spans = soup.select("td[class='Formule']")

    return split_spans_by_date(dates=dates, spans=spans)


def list_slots() -> Sequence[Slot]:
    """
    Lists all the slots listed on the Calypso website.
    :return: The list of slots, available or not.
    """
    response = requests.get(URL, verify=True)
    response.raise_for_status()

    return parse_planning_html(response.text)


def print_available_slots(available_slots: List[Slot]) -> None:
    def format_slot(slot: Slot) -> str:
        return (
            f"{slot.start_datetime.strftime('%A %d/%m')}: "
            f"{slot.start_datetime.strftime('%H:%M')} - {slot.end_datetime.strftime('%H:%M')}: "
            f"{slot.remaining_places} place(s)"
        )

    if available_slots:
        print(f"{len(available_slots)} slot(s) open at the moment:")
        print(os.linesep.join(format_slot(slot) for slot in available_slots))
    else:
        print("No slot available at the moment.")


def main():
    slots = list_slots()
    available_slots = [s for s in slots if s.remaining_places > 0]
    print_available_slots(available_slots)


if __name__ == "__main__":
    main()
