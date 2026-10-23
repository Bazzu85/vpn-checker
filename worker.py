import os
import json
import time
import shutil
import subprocess
import psutil

# Percorso della cartella CONFIG rispetto alla posizione dello script
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "CONFIG")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def carica_configurazione():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Errore nella lettura del file di configurazione: {e}")
        return None

def risolvi_percorso_eseguibile(proc):
    percorso = os.path.expandvars(os.path.expanduser(proc.strip().strip('"')))
    if os.path.isfile(percorso):
        return os.path.abspath(percorso)
    return shutil.which(percorso)

def main():
    print("=== WORKER AVVIATO ===")
    print("Premi CTRL+C per interrompere lo script.\n")
    
    while True:
        config = carica_configurazione()
        
        if not config:
            print("File di configurazione non trovato nella cartella CONFIG. In attesa...")
            time.sleep(5)
            continue
            
        interfaccia = config.get("interface")
        processi = config.get("processes", [])
        
        # Verifica se l'interfaccia di rete esiste ed è attiva (isup)
        stats_reti = psutil.net_if_stats()
        if interfaccia in stats_reti and stats_reti[interfaccia].isup:
            # Ottieni i nomi dei processi attualmente attivi (in minuscolo per un confronto robusto)
            processi_attivi = {p.info['name'].lower() for p in psutil.process_iter(['name']) if p.info['name']}
            
            for proc in processi:
                nome_proc = os.path.basename(proc).lower()
                if nome_proc not in processi_attivi:
                    print(f"[ATTENZIONE] Processo '{proc}' non attivo. Avvio in corso...")
                    percorso = risolvi_percorso_eseguibile(proc)
                    if not percorso:
                        print(f"[ERRORE] Eseguibile '{proc}' non trovato. Inserisci nel configuratore il percorso completo del file .exe.")
                        continue
                    try:
                        subprocess.Popen([percorso])
                    except Exception as e:
                        print(f"Errore durante l'avvio del processo {proc}: {e}")
        else:
            print(f"Interfaccia di rete '{interfaccia}' non connessa o non trovata.")
            
        # Intervallo di controllo (es. ogni 10 secondi)
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nWorker interrotto dall'utente.")
    
    input("Premi INVIO per chiudere...")