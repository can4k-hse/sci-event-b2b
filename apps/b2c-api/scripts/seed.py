import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User

SCIENTISTS = [
    {
        "phone": "+79161000001",
        "name": "Алексей",
        "surname": "Семёнов",
        "organization": "МГУ им. М.В. Ломоносова",
        "interests": ["квантовая механика", "физика конденсированного состояния", "сверхпроводимость"],
    },
    {
        "phone": "+79161000002",
        "name": "Екатерина",
        "surname": "Воронова",
        "organization": "Институт биоорганической химии РАН",
        "interests": ["структурная биология", "криоэлектронная микроскопия", "белковая инженерия"],
    },
    {
        "phone": "+79161000003",
        "name": "Дмитрий",
        "surname": "Захаров",
        "organization": "ЦЕРН",
        "interests": ["физика элементарных частиц", "детекторы", "Большой адронный коллайдер"],
    },
    {
        "phone": "+79161000004",
        "name": "Maria",
        "surname": "Petrova",
        "organization": "MIT — Computer Science & AI Lab",
        "interests": ["машинное обучение", "обработка естественного языка", "нейронные сети"],
    },
    {
        "phone": "+79161000005",
        "name": "Иван",
        "surname": "Козловский",
        "organization": "СПбГУ — физический факультет",
        "interests": ["астрофизика", "гравитационные волны", "нейтронные звёзды"],
    },
    {
        "phone": "+79161000006",
        "name": "Анна",
        "surname": "Белова",
        "organization": "Институт химической физики РАН",
        "interests": ["катализ", "зелёная химия", "топливные элементы"],
    },
    {
        "phone": "+79161000007",
        "name": "Sergei",
        "surname": "Novikov",
        "organization": "Stanford University — Department of Genetics",
        "interests": ["геномика", "CRISPR", "эволюционная биология"],
    },
    {
        "phone": "+79161000008",
        "name": "Ольга",
        "surname": "Тихонова",
        "organization": "Сколтех",
        "interests": ["квантовые вычисления", "квантовая криптография", "алгоритмы"],
    },
    {
        "phone": "+79161000009",
        "name": "Николай",
        "surname": "Фёдоров",
        "organization": "Новосибирский государственный университет",
        "interests": ["вычислительная нейронаука", "когнитивные системы", "нейроинтерфейсы"],
    },
    {
        "phone": "+79161000010",
        "name": "Лариса",
        "surname": "Громова",
        "organization": "Институт океанологии РАН",
        "interests": ["климатология", "океанография", "изменение климата"],
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing = set(
            row[0]
            for row in (await session.execute(select(User.phone))).all()
        )

        new_users = [
            User(**data, push_enabled=True)
            for data in SCIENTISTS
            if data["phone"] not in existing
        ]

        if not new_users:
            print("Seed: все пользователи уже существуют, пропускаем.")
            return

        session.add_all(new_users)
        await session.commit()
        print(f"Seed: добавлено {len(new_users)} пользователей.")


if __name__ == "__main__":
    asyncio.run(seed())
