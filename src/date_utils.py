from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional



def subtractWorkingMinutes(
    end_date: datetime,
    total_minutes: float,
    start_work: time,
    end_work: time,
    holiday_list: List[Dict[str, Any]],
    lunch_start: time,
    lunch_end: time,
    pausa_duration: timedelta,
) -> datetime:
    """
    Sottrae 'total_minutes' minuti lavorativi dalla 'end_date'.
    Rispetta orari di lavoro, pause pranzo, weekend e ferie.
    Esempio di implementazione presa dal tuo snippet.
    """
    current_date = end_date
    minutes_remaining = total_minutes

    # Calcolo minuti lavorativi giornalieri:
    # (chiusura - apertura) - pausa pranzo
    working_minutes_per_day = (
        datetime.combine(datetime.min, end_work)
        - datetime.combine(datetime.min, start_work)
        - pausa_duration
    ).total_seconds() / 60

    while minutes_remaining > 0:
        # Vado al giorno precedente (inizio giornata)
        current_date -= timedelta(days=1)

        # Skip weekend (sabato=5, domenica=6)
        if current_date.weekday() >= 5:
            continue

        # Skip holidays
        is_holiday = False
        for hol in holiday_list:
            # ipotizziamo che holiday_list contenga oggetti con "inizio" e "fine"
            # come datetime
            inizio = hol["inizio"]
            fine = hol["fine"]
            if inizio.date() <= current_date.date() <= fine.date():
                is_holiday = True
                break
        if is_holiday:
            continue

        # Se i minuti da sottrarre >= minuti lavorativi di un giorno
        if minutes_remaining >= working_minutes_per_day:
            minutes_remaining -= working_minutes_per_day
        else:
            # Rimangono meno minuti di un'intera giornata
            minutes_to_subtract_today = minutes_remaining

            # Inizio della giornata lavorativa
            current_date = current_date.replace(
                hour=start_work.hour,
                minute=start_work.minute,
                second=0,
                microsecond=0
            )
            # Aggiungo i minuti da sottrarre (che in realtà vado indietro nel tempo)
            current_date += timedelta(minutes=minutes_to_subtract_today)

            minutes_remaining = 0
            return current_date

        # Finito di usare questa giornata, mi porto a inizio giornata
        current_date = current_date.replace(
            hour=start_work.hour,
            minute=start_work.minute,
            second=0,
            microsecond=0
        )

    return current_date