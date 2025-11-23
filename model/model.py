from database.regione_DAO import RegioneDAO
from database.tour_DAO import TourDAO
from database.attrazione_DAO import AttrazioneDAO

class Model:
    def __init__(self):
        self.tour_map = {}  # Mappa ID tour -> oggetti Tour
        self.attrazioni_map = {}  # Mappa ID attrazione -> oggetti Attrazione

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0
        self._tour_attrazione = {}
        self._tour_attrazioni = {}
        self.attrazioni_usate_set = set()  # <-- set aggiornato delle attrazioni usate

        # Caricamento
        self.load_tour()
        self.load_attrazioni()
        self.load_relazioni()

    @staticmethod
    def load_regioni():
        """ Restituisce tutte le regioni disponibili """
        return RegioneDAO.get_regioni()

    def load_tour(self):
        """ Carica tutti i tour in un dizionario [id, Tour]"""
        self.tour_map = TourDAO.get_tour()

    def load_attrazioni(self):
        """ Carica tutte le attrazioni in un dizionario [id, Attrazione]"""
        self.attrazioni_map = AttrazioneDAO.get_attrazioni()

    def load_relazioni(self):
        """
        Costruisce la mappa self._tour_attrazioni: {tour_id: [attr_id, ...]}
        Assume che TourDAO.get_tour_attrazioni() ritorni un dict {tour_id: [attr_id,...]}
        """
        relazioni = TourDAO.get_tour_attrazioni()
        self._tour_attrazioni = {}

        for relazione in relazioni:
            tour_id = relazione["id_tour"]
            attr_id = relazione["id_attrazione"]
            if tour_id not in self._tour_attrazioni:
                self._tour_attrazioni[tour_id] = []
            self._tour_attrazioni[tour_id].append(attr_id)

    def genera_pacchetto(self, id_regione: str, max_giorni: int = None, max_budget: float = None):
        """ Prepara i candidati e avvia la ricorsione """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1
        self._max_giorni = max_giorni
        self._max_budget = max_budget

        # lista candidati solo per la regione
        self._tour_filtrati = []
        for tour_id, tour in self.tour_map.items():
            if tour.id_regione == id_regione:
                self._tour_filtrati.append((tour_id, tour))

        # avvio ricorsione
        self._ricorsione(0, [], 0, 0.0, 0, set())

        # calcolo costo totale del pacchetto ottimo
        costo_totale = 0.0
        for tour in self._pacchetto_ottimo:
            costo_totale += float(tour.costo)
        self._costo = costo_totale

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, attrazioni_usate: set):
        """ Backtracking sui candidati """
        if index >= len(self._tour_filtrati):
            if valore_corrente > self._valore_ottimo:
                self._valore_ottimo = valore_corrente
                self._pacchetto_ottimo = list(pacchetto_parziale)

            return

        # ramo 1: salto il candidato
        self._ricorsione(index + 1, pacchetto_parziale, durata_corrente, costo_corrente, valore_corrente, set(attrazioni_usate))

        # ramo 2: includo il candidato corrente
        tour_id, tour_attributi = self._tour_filtrati[index]

        durata_aggiuntiva = int(tour_attributi.durata_giorni)
        costo_aggiuntivo = float(tour_attributi.costo)

        valore_aggiuntivo = 0
        id_nuove_attrazioni = []
        id_attrazioni_tour = self._tour_attrazioni.get(tour_id, [])
        for id_attrazione in id_attrazioni_tour:
            if id_attrazione not in attrazioni_usate:
                id_nuove_attrazioni.append(id_attrazione)
                attributi_attrazione = self.attrazioni_map.get(id_attrazione)
                if attributi_attrazione is not None:
                    valore_aggiuntivo += int(attributi_attrazione.valore_culturale)


        nuova_durata = durata_corrente + durata_aggiuntiva
        nuovo_costo = costo_corrente + costo_aggiuntivo

        if ((self._max_giorni is None) or (nuova_durata <= self._max_giorni)) and ((self._max_budget is None) or (nuovo_costo <= self._max_budget)):
            pacchetto_parziale.append(tour_attributi)
            new_used = set(attrazioni_usate)
            new_used.update(id_nuove_attrazioni)

            # aggiornamento set leggibile delle attrazioni usate nel pacchetto ottimo
            if valore_corrente + valore_aggiuntivo > self._valore_ottimo:
                self.attrazioni_usate_set = set(new_used)
                print(self.attrazioni_usate_set)

            # ricorsione sul candidato successivo
            self._ricorsione(index + 1, pacchetto_parziale, nuova_durata, nuovo_costo, valore_corrente + valore_aggiuntivo, new_used)

            pacchetto_parziale.pop()
        return