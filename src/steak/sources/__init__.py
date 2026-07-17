from steak import cfg
from steak.sources.apple_music import AppleMusicBase
from steak.sources.bandcamp import BandcampBase
from steak.sources.beatport import BeatportBase
from steak.sources.deezer import DeezerBase
from steak.sources.discogs import DiscogsBase
from steak.sources.musicbrainz import MusicBrainzBase
from steak.sources.qobuz import QobuzBase
from steak.sources.tidal import TidalBase

__all__ = [
    "cfg",
    "BandcampBase",
    "BeatportBase",
    "DeezerBase",
    "DiscogsBase",
    "AppleMusicBase",
    "MusicBrainzBase",
    "QobuzBase",
    "TidalBase",
    "SOURCE_ICONS",
]

SOURCE_ICONS = {
    "Bandcamp": "https://ptpimg.me/91oo89.png",
    "Beatport": "https://ptpimg.me/5hwjpv.png",
    "Deezer": "https://ptpimg.me/m265v2.png",
    "Discogs": "https://ptpimg.me/mt4ql3.png",
    "Apple Music": "https://ptpimg.me/0z2x90.png",
    "MusicBrainz": "https://ptpimg.me/56plwd.png",
    "Qobuz": "https://redacted.sh/i/34vFQi9EGOI.png",
    "Tidal": "https://ptpimg.me/5vxo23.png",
}
