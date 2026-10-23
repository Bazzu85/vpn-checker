import os
import json
import psutil

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "CONFIG")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

def chiedi_si_no(messaggio):
    """Chiede all'utente un input S/N ripetendo la domanda in caso di errore."""
    while True:
        risposta = input(f"{messaggio} (s/n): ").strip().lower()
        if risposta in ('s', 'si', 'sì', 'y', 'yes'):
            return True
        elif risposta in ('n', 'no'):
            return False
        print("Valore non valido. Inserire 's' per sì o 'n' per no.")

def elenca_e_scegli_interfaccia():
    interfacce = list(psutil.net_if_stats().keys())
    print("\nInterfacce di rete disponibili:")
    for idx, iface in enumerate(interfacce, 1):
        print(f"  {idx}. {iface}")
    
    while True:
        try:
            scelta = int(input("Scegli il numero dell'interfaccia da configurare: "))
            if 1 <= scelta <= len(interfacce):
                return interfacce[scelta - 1]
        except ValueError:
            pass
        print("Scelta non valida. Riprova.")

def ottieni_processi_attivi_ordinati():
    procs = {}
    for p in psutil.process_iter(['name', 'exe']):
        try:
            nome = p.info.get('name')
            percorso = p.info.get('exe')
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        if nome:
            chiave = percorso.casefold() if percorso else nome.casefold()
            procs.setdefault(chiave, (nome, percorso))
    return sorted(procs.values(), key=lambda proc: (proc[0].lower(), (proc[1] or '').lower()))

def chiave_processo(proc):
    percorso = os.path.expandvars(os.path.expanduser(proc.strip().strip('"')))
    return os.path.basename(percorso).casefold()

def gestisci_aggiunta_processi(lista_processi):
    manuale = chiedi_si_no("Vuoi inserire a mano i processi windows da aggiungere?")
    if manuale:
        while True:
            while True:
                proc = input("Inserisci il percorso completo del file .exe (es. C:\\Program Files\\app\\app.exe): ").strip().strip('"')
                percorso = os.path.expandvars(os.path.expanduser(proc))
                if not os.path.isabs(percorso):
                    print("Percorso non completo: inserisci un percorso assoluto, ad esempio C:\\Program Files\\app\\app.exe.")
                    continue
                if not percorso.lower().endswith('.exe') or not os.path.isfile(percorso):
                    print("File .exe non trovato: controlla il percorso in Esplora file e inseriscilo di nuovo.")
                    continue
                proc = os.path.abspath(percorso)
                break

            if not any(chiave_processo(esistente) == chiave_processo(proc) for esistente in lista_processi):
                lista_processi.append(proc)
                print(f"Processo '{proc}' aggiunto.")
            else:
                print("Il processo è già presente nella configurazione.")
            
            if not chiedi_si_no("Vuoi inserire un altro processo?"):
                break
    else:
        attivi = ottieni_processi_attivi_ordinati()
        print("\nProcessi attivi sul sistema:")
        for idx, (nome, percorso) in enumerate(attivi, 1):
            dettaglio = percorso or "percorso non disponibile"
            print(f"  {idx}. {nome} - {dettaglio}")
            
        scelte = input("Inserisci i numeri dei processi da aggiungere separati da spazio (es. 1 3 5): ").strip()
        try:
            indici = [int(x) for x in scelte.split()]
            for idx in indici:
                if 1 <= idx <= len(attivi):
                    nome_proc, percorso = attivi[idx - 1]
                    valore_configurazione = percorso or nome_proc
                    if not any(chiave_processo(esistente) == chiave_processo(valore_configurazione) for esistente in lista_processi):
                        lista_processi.append(valore_configurazione)
                        print(f"Processo '{valore_configurazione}' aggiunto.")
                    else:
                        print(f"Processo '{nome_proc}' già presente nella configurazione.")
                else:
                    print(f"Indice {idx} non valido, saltato.")
        except ValueError:
            print("Formato non valido. Nessun processo aggiunto.")

def main():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # Controllo se il file di configurazione esiste
    if not os.path.exists(CONFIG_FILE):
        print("=== CONFIGURATORE: Nuova Configurazione ===")
        interfaccia = elenca_e_scegli_interfaccia()
        processi = []
        
        gestisci_aggiunta_processi(processi)
        
        config = {
            "interface": interfaccia,
            "processes": processi
        }
        
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        print(f"\nConfigurazione creata e salvata con successo in: {CONFIG_FILE}")
        
    else:
        print("=== CONFIGURATORE: Modifica Configurazione Esistente ===")
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {"interface": "", "processes": []}
            
        print(f"Interfaccia di rete attuale: {config.get('interface', 'Nessuna')}")
        
        if chiedi_si_no("Vuoi cambiare l'interfaccia di rete?"):
            config['interface'] = elenca_e_scegli_interfaccia()
            
        processi = config.get('processes', [])
        
        # Loop di gestione processi (aggiunta e rimozione)
        while True:
            print("\n--- Elenco attuale dei processi configurati ---")
            if not processi:
                print("  (Nessun processo configurato)")
            else:
                for idx, p in enumerate(processi, 1):
                    print(f"  ID {idx}: {p}")
                    
            if chiedi_si_no("Vuoi aggiungere un processo?"):
                gestisci_aggiunta_processi(processi)
                continue
                
            if processi and chiedi_si_no("Vuoi rimuovere un processo?"):
                while processi:
                    try:
                        id_rem = int(input("Inserisci l'ID del processo da rimuovere: "))
                        if 1 <= id_rem <= len(processi):
                            rimosso = processi.pop(id_rem - 1)
                            print(f"Processo '{rimosso}' rimosso con successo.")
                        else:
                            print("ID non valido.")
                            break
                    except ValueError:
                        print("Inserisci un numero intero valido.")
                        break

                    if not processi or not chiedi_si_no("Vuoi rimuovere un altro processo?"):
                        break

                    print("\n--- Elenco aggiornato dei processi configurati ---")
                    for idx, processo in enumerate(processi, 1):
                        print(f"  ID {idx}: {processo}")
                    
            if not chiedi_si_no("Vuoi effettuare altre modifiche ai processi?"):
                break
                
        config['processes'] = processi
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        print(f"\nConfigurazione aggiornata e salvata in: {CONFIG_FILE}")

if __name__ == "__main__":
    main()
    input("Premi INVIO per chiudere...")