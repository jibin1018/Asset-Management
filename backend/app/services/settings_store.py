import json

from sqlalchemy.orm import Session

from ..models import Setting
from ..schemas import SettingsModel


def get_settings(db: Session) -> SettingsModel:
    values = {s.key: json.loads(s.value) for s in db.query(Setting).all()}
    known = {k: v for k, v in values.items() if k in SettingsModel.model_fields}
    return SettingsModel(**known)


def save_settings(db: Session, settings: SettingsModel) -> SettingsModel:
    for key, value in settings.model_dump().items():
        db.merge(Setting(key=key, value=json.dumps(value)))
    db.commit()
    return settings
