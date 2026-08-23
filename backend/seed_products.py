import random
from pathlib import Path

from app import models
from app.database import Base, SessionLocal, engine

IMAGE_DIR = Path('/app/../frontend/product-images')
PRODUCTS = [
    ('Oversize sport futbolka', 'Yengil va kundalik uslub uchun qulay oversize futbolka.', '5f91b9d05f9a6fdcb4a387b1e06a3ae0.jpg'),
    ('Color Streetwear futbolka', 'Yorqin printli, zamonaviy streetwear uslubidagi futbolka.', '9ea436dabb5c8bee1e6bd251137606fa.jpg'),
    ('Pikachu print futbolka', 'Yumshoq matoli, quvnoq Pikachu printli oq futbolka.', 'b0294756c946e70e9faae3b21982a2ac.jpg'),
    ('Yashil chiziqli kombinezon', 'Yashil chiziqli, yozgi obrazlar uchun yengil kombinezon.', 'b5d3f294c4b000923516eec6a07e487a.jpg'),
    ('Tim Yi klassik futbolka', 'Minimalistik yozuvli, kundalik kiyimga mos oq futbolka.', 'c02ebb7c5e240fbf5f832585dd060acf.jpg'),
    ('Moviy casual kostyum', 'Sport va sayr uchun qulay moviy futbolka va shim to‘plami.', 'c0d44ca3c51b58c53d9e131c07e0f4be.jpg'),
    ('Moviy yozgi kostyum', 'Yengil matoli, dengiz bo‘yidagi yozgi obraz uchun kostyum.', 'd2f4fc0d3859da895cc5fe803adc5d8e.jpg'),
    ('Oq oversize svitshot', 'Keng bichimli, yumshoq va iliq oq svitshot.', 'e7f48cfdbdba5c341b1c98ebfa45d7b7.jpg'),
    ('Moviy naqshli ko‘ylak', 'Gulli naqshli, nafis va o‘ziga xos moviy ko‘ylak.', 'f6b07a493e545c524ff71e9f0854706d.jpg'),
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    rng = random.Random(20260823)
    try:
        added = 0
        for name, description, filename in PRODUCTS:
            image_url = f'/product-images/{filename}'
            if db.query(models.Product).filter(models.Product.image_url == image_url).first():
                continue
            price = rng.randrange(50000, 250001, 5000)
            product = models.Product(
                name=name,
                category='kiyim',
                emoji='👗',
                description=description,
                image_url=image_url,
            )
            db.add(product)
            db.flush()
            for color, color_code in [('Oq', '#ffffff'), ('Ko‘k', '#2563eb')]:
                for size in ('S', 'M', 'X'):
                    db.add(models.Variant(
                        product_id=product.id,
                        label=size,
                        color=color_code,
                        price=price,
                        stock_qty=10,
                    ))
            added += 1
        db.commit()
        print(f'added: {added}, total products: {db.query(models.Product).count()}')
    finally:
        db.close()


if __name__ == '__main__':
    seed()
