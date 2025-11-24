from database.regione_DAO import RegioneDAO
from database.tour_DAO import TourDAO
from database.attrazione_DAO import AttrazioneDAO


class Model:
    def __init__(self):
        self.tour_map = {}  # Mappa ID tour -> oggetti Tour
        self.attrazioni_map = {}  # Mappa ID attrazione -> oggetti Attrazione

        self._pacchetto_ottimo = []  # Lista finale dei tour migliori
        self._valore_ottimo: int = -1  # Valore culturale massimo trovato
        self._costo = 0  # Costo totale del pacchetto ottimo
        self._tour_attrazione = {}  # (non usato direttamente)
        self._tour_attrazioni = {}  # Mappa tour_id -> lista/insieme di attrazioni
        self.attrazioni_usate_set = set()  # Attrazioni usate dal pacchetto ottimo

        # Caricamento dati da DB
        self.load_tour()
        self.load_attrazioni()
        self.load_relazioni()

    @staticmethod
    def load_regioni():
        """ Restituisce tutte le regioni disponibili """
        return RegioneDAO.get_regioni()  # Richiede lista regioni dal DAO

    def load_tour(self):
        """ Carica tutti i tour in un dizionario [id, Tour]"""
        self.tour_map = TourDAO.get_tour()  # Ottiene tutti i tour dal DB

    def load_attrazioni(self):
        """ Carica tutte le attrazioni in un dizionario [id, Attrazione]"""
        self.attrazioni_map = AttrazioneDAO.get_attrazioni()  # Ottiene tutte le attrazioni dal DB

    def load_relazioni(self):
        """
        Costruisce la mappa self._tour_attrazioni: {tour_id: [attr_id, ...]}
        Assume che TourDAO.get_tour_attrazioni() ritorni una lista di dict
        """
        relazioni = TourDAO.get_tour_attrazioni()  # Ottiene la tabella tour-attrazioni
        self._tour_attrazioni = {}  # Reset struttura

        for relazione in relazioni:  # Per ogni riga relazione
            tour_id = relazione["id_tour"]  # Prendo ID tour
            attr_id = relazione["id_attrazione"]  # Prendo ID attrazione
            if tour_id not in self._tour_attrazioni:  # Se non esiste ancora
                self._tour_attrazioni[tour_id] = []  # Creo lista
            self._tour_attrazioni[tour_id].append(attr_id)  # Aggiungo attrazione al tour

    def genera_pacchetto(self, id_regione: str, max_giorni: int = None, max_budget: float = None):
        """ Prepara i candidati e avvia la ricorsione """
        self._pacchetto_ottimo = []  # Reset pacchetto ottimo
        self._costo = 0  # Reset costo totale
        self._valore_ottimo = -1  # Reset valore massimo
        self._max_giorni = max_giorni  # Vincolo giorni
        self._max_budget = max_budget  # Vincolo budget

        # Filtra tour appartenenti alla regione scelta
        self._tour_filtrati = []
        for tour_id, tour in self.tour_map.items():  # Controllo tutti i tour
            if tour.id_regione == id_regione:  # Se il tour appartiene alla regione selezionata
                self._tour_filtrati.append((tour_id, tour))  # Lo aggiungo ai candidati

        # Avvia backtracking
        self._ricorsione(0, [], 0, 0.0, 0, set())

        # Calcolo costo totale e assegno attrazioni reali ai tour selezionati
        costo_totale = 0.0
        for tour in self._pacchetto_ottimo:  # Per ogni tour scelto
            costo_totale += float(tour.costo)  # Sommo costo
            tour_id = getattr(tour, "id", None)  # Prendo ID del tour
            if tour_id is not None:
                attr_ids_this_tour = set(self._tour_attrazioni.get(tour_id, []))  # Tutte le attrazioni del tour
                attr_ids_effettive = attr_ids_this_tour.intersection(
                    self.attrazioni_usate_set)  # Solo quelle usate davvero
                formattata = []
                for aid in attr_ids_effettive:  # Per ogni attrazione selezionata del tour
                    a = self.attrazioni_map.get(aid)  # Recupera oggetto Attrazione
                    if a is not None:
                        formattata.append(f"{a.nome} ({a.valore_culturale})")  # Formatta “nome (valore)”
                tour.attrazioni = formattata  # Assegna lista finale delle attrazioni
            else:
                tour.attrazioni = []  # Se manca ID (non dovrebbe succedere)

        self._costo = costo_totale  # Aggiorna costo totale

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo  # Ritorna risultato finale

    def _ricorsione(self, index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float,
                    valore_corrente: int, attrazioni_usate: set):
        """ Backtracking sui candidati """

        # Caso base: esauriti i tour
        if index >= len(self._tour_filtrati):
            if valore_corrente > self._valore_ottimo:  # Se la soluzione è migliore
                self._valore_ottimo = valore_corrente  # Aggiorna valore
                self._pacchetto_ottimo = list(pacchetto_parziale)  # Salva soluzione
                self.attrazioni_usate_set = set(attrazioni_usate)  # Salva attrazioni usate
            return  # Termina ramo

        # RAMO 1: salto il tour corrente
        self._ricorsione(index + 1, pacchetto_parziale, durata_corrente, costo_corrente, valore_corrente,
                         set(attrazioni_usate))

        # RAMO 2: includo il tour corrente
        tour_id, tour_attributi = self._tour_filtrati[index]  # Prendo ID e oggetto Tour

        durata_aggiuntiva = int(tour_attributi.durata_giorni)  # Giorni richiesti dal tour
        costo_aggiuntivo = float(tour_attributi.costo)  # Costo del tour

        # Recupero tutte le attrazioni del tour corrente
        id_attrazioni_tour = set(self._tour_attrazioni.get(tour_id, []))

        # Se una attrazione è già stata usata, non posso mettere questo tour
        if id_attrazioni_tour & attrazioni_usate:  # Intersezione non vuota → attrazione condivisa
            return  # Scarto ramo

        id_nuove_attrazioni = list(id_attrazioni_tour)  # Le nuove attrazioni aggiunte
        valore_aggiuntivo = 0
        for id_attrazione in id_nuove_attrazioni:  # Sommo valore culturale
            attributi_attrazione = self.attrazioni_map.get(id_attrazione)
            if attributi_attrazione is not None:
                valore_aggiuntivo += int(attributi_attrazione.valore_culturale)

        nuova_durata = durata_corrente + durata_aggiuntiva  # Aggiorna durata
        nuovo_costo = costo_corrente + costo_aggiuntivo  # Aggiorna costo

        # Rispetto dei vincoli tempo/budget
        if ((self._max_giorni is None) or (nuova_durata <= self._max_giorni)) and \
                ((self._max_budget is None) or (nuovo_costo <= self._max_budget)):
            pacchetto_parziale.append(tour_attributi)  # Aggiungo il tour al pacchetto
            new_used = set(attrazioni_usate)  # Copio attrazioni usate
            new_used.update(id_nuove_attrazioni)  # Aggiungo nuove attrazioni

            # Ricorsione successiva
            self._ricorsione(index + 1, pacchetto_parziale, nuova_durata, nuovo_costo,
                             valore_corrente + valore_aggiuntivo, new_used)

            pacchetto_parziale.pop()  # Backtracking: rimuovo il tour

        return  # Fine ramo
