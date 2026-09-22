attendees = [
    {
        "name": "Linda",
        "country": "US",
        "ticket_type": "full",
    },
    {
        "name": "Zara",
        "country": "UK",
        "ticket_type": "student",
    },
    {
        "name": "Mina",
        "country": "US",
        "ticket_type": "student",
    },
    {
        "name": "Oscar",
        "country": "DK",
        "ticket_type": "full",
    },
    {
        "name": "Alba",
        "country": "UK",
        "ticket_type": "full",
    },
]
dict_of_lists = {}
for attendee in attendees:
    country = attendee["country"]
    if country not in dict_of_lists:
        dict_of_lists[country] = []
    dict_of_lists[country].append(attendee)
sorted_by_key = sorted(dict_of_lists.items())
for country, attendees in sorted_by_key:
    print(f"Country: {country}")
    print(f"Number of Attendees: {len(attendees)}")
    names = ""
    for attendee in attendees:
        names += attendee["name"] + " "
    print(f"Names: {names} \n")
