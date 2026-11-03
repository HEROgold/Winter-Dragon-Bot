<!-- GENERATED FILE - do not hand-edit. Regenerate with: uv run python scripts/generate_command_docs.py -->

# /fuel

Track your car's refuels and fuel efficiency.

Log each time you fill your car's tank, and see how many kilometres you get per litre (or litres per 100 km) over time. Your logs are yours; other members can't see them.

## Commands

- [`/fuel add`](#add): Log a refuel: total price, distance driven since the last one, fuel added, optional YYYY-MM-DD date
- [`/fuel efficiency`](#efficiency): Show a graph of your fuel efficiency over time, in your units
- [`/fuel units`](#units): Pick how your fuel efficiency is shown: km/L or L/100km

## /fuel add {#add}

Log a refuel: total price, distance driven since the last one, fuel added, optional YYYY-MM-DD date.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `price` | number | yes | The total price of the refuel |
| `distance` | number | yes | The distance driven since the last refuel |
| `amount` | number | yes | The amount of fuel added |
| `date` | text | no | The day of the refuel as YYYY-MM-DD, now when left out |

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/fuel add price:62.40 distance:640 amount:41.2`.

    The bot answers with an embed; only you see it:

    > Logged a refuel of 41.2 for 62.4 after 640: 15.53 km/L.
    > Use /fuel efficiency to see how that changes over time.

## /fuel efficiency {#efficiency}

Show a graph of your fuel efficiency over time, in your units.

It takes no options.

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/fuel efficiency`.

    The bot answers with an image; only you see it:

    > A line graph of your fuel efficiency over time, in your units.

## /fuel units {#units}

Pick how your fuel efficiency is shown: km/L or L/100km.

| Option | Type | Required | What it is |
| --- | --- | --- | --- |
| `units` | text | yes | km/L or L/100km |

**Who can run it:** Anyone, in a server or in DMs.

!!! example "Example"
    You type `/fuel units units:L/100km`.

    The bot answers with a message; only you see it:

    > Your fuel efficiency is now shown in L/100km.
