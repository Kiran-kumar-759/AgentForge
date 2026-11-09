from typing import Dict, List
from app.services.data.base import MarineDataProvider
from app.services.data.providers.open_meteo import OpenMeteoProvider
from app.services.data.providers.noaa_erddap import NoaaErddapProvider
from app.services.data.providers.nasa_earthdata import NasaEarthdataProvider
from app.services.data.providers.mosdac import MosdacProvider

class ProviderRegistry:
    def __init__(self):
        self.providers: Dict[str, MarineDataProvider] = {
            "Open-Meteo": OpenMeteoProvider(),
            "NOAA": NoaaErddapProvider(),
            "NASA Earthdata": NasaEarthdataProvider(),
            "MOSDAC": MosdacProvider(),
        }
        
    def get_provider(self, name: str) -> MarineDataProvider:
        if name not in self.providers:
            raise ValueError(f"Unknown provider: {name}")
        return self.providers[name]
        
    def get_all_providers(self) -> List[MarineDataProvider]:
        return list(self.providers.values())
