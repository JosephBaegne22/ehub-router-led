# receiver/config_loader.py
import pandas as pd

def load_band_from_excel(xlsx_path: str, universe: int):
    """
    Charge UNE ligne (bande/univers) depuis l'Excel pour l'univers demandé.
    Retourne un dict: {entity_start, entity_end, ip, universe}.
    """
    df = pd.read_excel(xlsx_path, sheet_name="eHuB")
    df = df.rename(columns={
        "Entity Start": "entity_start",
        "Entity End": "entity_end",
        "ArtNet IP": "ip",
        "ArtNet Universe": "universe",
        "Name": "name",
    })
    row = df[df["universe"] == universe].head(1)
    if row.empty:
        raise ValueError(f"Aucune ligne trouvée pour l'univers {universe} dans {xlsx_path}")
    r = row.iloc[0]
    return {
        "entity_start": int(r["entity_start"]),
        "entity_end": int(r["entity_end"]),
        "ip": str(r["ip"]),
        "universe": int(r["universe"]),
        "name": str(r.get("name", f"universe_{universe}")),
    }
