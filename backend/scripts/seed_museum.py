# ============================================================
# 智绘锡承 - 惠山泥人数字博物馆馆藏种子数据
# 位置: backend/scripts/seed_museum.py
#
# 作用: 将工商同学整理的 10 件惠山泥人馆藏作品导入 Artwork 表，
#       由「惠山数字博物馆」官方账号持有；前端博物馆页"馆藏珍品"
#       板块与社区页均可通过作品接口展示。
# 数据: 文案源自 operations/docs/02_数字博物馆展品文案.md
#       图片位于 app/static/uploads/museum/（源自中国非物质文化遗产网）
# 运行: cd backend && .\.venv\Scripts\python.exe scripts\seed_museum.py
# 幂等: 按 (user_id, title) 判重，重复执行不会产生重复数据。
# ============================================================
import os
import sys
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.artwork import Artwork
from app.models.user import User

# --- 官方馆藏账号 ---
MUSEUM_EMAIL = 'museum@zhihuixicheng.com'
MUSEUM_USERNAME = '惠山数字博物馆'
MUSEUM_PASSWORD = os.getenv('MUSEUM_SEED_PASSWORD') or secrets.token_urlsafe(32)

IMAGE_BASE = '/api/static/uploads/museum'

# --- 10 件馆藏展品（文案见 operations/docs/02_数字博物馆展品文案.md） ---
EXHIBITS = [
    {
        'title': '《藕囡》',
        'image': '01_ounian.jpg',
        'description': (
            '无锡自古藕塘连片，"藕囡"是对水乡女娃的昵称。作品以惠山乌土手捏成型，'
            '女孩双髻乌亮、怀中白藕饱满，衣纹用极浅的浮雕手法压出，彩绘以粉、白、青三色为主，'
            '清雅如一泓荷塘水。艺人抓住孩童含笑低眉的一瞬，把江南的温润都收进了这方寸之间。'
        ),
        'tags': ['惠山泥人', '数字博物馆', '细货', '孩童', '江南风情'],
    },
    {
        'title': '《百年好合》',
        'image': '02_bainianhaoh.jpg',
        'description': (
            '"百年好合"是惠山泥人中最常见的婚嫁贺礼题材。童男童女各执莲花、莲蓬，'
            '取"莲"谐"连"、"合"之意；造型沿用模具印制，色彩大红大绿、饱满明艳，'
            '是"粗货"喜庆美学的典型代表。过去无锡人家嫁女儿，总要在妆奁里放上一对，'
            '让泥土替长辈说出那句最重的祝福。'
        ),
        'tags': ['惠山泥人', '数字博物馆', '粗货', '婚庆', '喜庆'],
    },
    {
        'title': '《雅媛》',
        'image': '03_yayuan.jpg',
        'description': (
            '仕女是手捏泥人中的经典题材。作品以"三分塑、七分彩"见功力：泥塑阶段将身姿捏出'
            '微微前倾的弧度，彩绘阶段再用细笔勾出眉眼，"开面"一笔定神。通体以青灰、月白为主调，'
            '只在头饰与衣缘点缀朱红，素雅端庄，恰似寄畅园里走出的一位读书人家女儿。'
        ),
        'tags': ['惠山泥人', '数字博物馆', '细货', '仕女', '素雅'],
    },
    {
        'title': '《福宝》',
        'image': '04_fubao.jpg',
        'description': (
            '"福宝"承袭大阿福一脉的造型基因：大头、圆身、盘膝而坐，怀抱象征福气的瑞兽。'
            '粗货不追求写实，而以夸张的圆润传递"福气满溢"的意象；彩绘纹样多用云纹与团花，'
            '颜色愈艳愈吉。这件作品至今仍是游客离开无锡时，最常带走的伴手礼。'
        ),
        'tags': ['惠山泥人', '数字博物馆', '粗货', '祈福', '阿福'],
    },
    {
        'title': '《花好月圆》',
        'image': '05_huahaoyueyuan.jpg',
        'description': (
            '作品将"花好"与"月圆"两大意象合于一器：人物衣袂上绘盛放牡丹，背景衬一轮满月式圆光。'
            '手捏泥人的"细"体现在指尖——花瓣层层贴塑，月晕以退晕技法层层罩染。'
            '中秋前后，这类题材在惠山街头最为俏销，人们相信泥塑的圆满能把团圆留得更久。'
        ),
        'tags': ['惠山泥人', '数字博物馆', '细货', '吉祥', '中秋'],
    },
    {
        'title': '《平安阿福》',
        'image': '06_pinganafu.jpg',
        'description': (
            '在大阿福经典的抱兽造型上，艺人添了一只宝瓶——"瓶"与"平"同音，寓意"平安是福"。'
            '脸部的"开面"是全器最精彩处：两弯笑眼以朱笔一笔带过，腮边一抹桃红，憨态可掬。'
            '老无锡人说，进门看见平安阿福，一年的奔波就有了着落。'
        ),
        'tags': ['惠山泥人', '数字博物馆', '粗货', '祈福', '阿福'],
    },
    {
        'title': '《团阿福》',
        'image': '07_tuanafu.jpg',
        'description': (
            '"团阿福"将人物体态尽量收拢成团，四肢几乎融于躯干，只留一颗笑容灿烂的脑袋——'
            '这是惠山粗货"以圆为美"的极致表达。民间观念里，"团"即团圆、聚合，'
            '孩子在怀中抱一个团阿福，等于把圆满抱在了身上。其造型对后来的卡通形象设计也颇有启发。'
        ),
        'tags': ['惠山泥人', '数字博物馆', '粗货', '祈福', '阿福'],
    },
    {
        'title': '《下雨了》',
        'image': '08_xiayule.jpg',
        'description': (
            '与常见的祈福题材不同，《下雨了》把镜头对准了日常：江南骤雨，孩童以袖掩头、'
            '缩颈疾步，憨态里带着一点狼狈的可爱。艺人以动态取胜——衣角翻飞、脚步欲走还留，'
            '连雨珠都用白釉点出。这类取材市井生活的作品，正是惠山泥人"人间烟火气"的最好注脚。'
        ),
        'tags': ['惠山泥人', '数字博物馆', '细货', '童趣', '市井'],
    },
    {
        'title': '《阿福》',
        'image': '09_afu.jpg',
        'description': (
            '传说古时惠山有猛兽为患，一对名唤"阿福"的孩童挺身搏兽、护佑乡邻，人们塑其像以纪念'
            '——这便是大阿福的由来。头绾双髻、笑容可掬、赤足盘膝、怀抱异兽，四百余年来经过'
            '一代代艺人再创作，造型愈发简练稳重。1992 年，大阿福被定为中国国际旅游年吉祥物，'
            '从惠山老街笑遍了全世界。'
        ),
        'tags': ['惠山泥人', '数字博物馆', '粗货', '阿福', '经典'],
    },
    {
        'title': '《三岔口》',
        'image': '10_sanchakou.jpg',
        'description': (
            '"手捏戏文"是惠山泥人登峰造极的品类：艺人常驻戏园看戏，散场后凭记忆捏出当夜名角身段。'
            '《三岔口》取自京剧经典武戏，任堂惠与刘利华摸黑对打、屏息试探的瞬间被凝固在泥胎上'
            '——翎口、靠旗、靴底无一处不精，脸谱开面一丝不苟。周恩来总理曾以手捏戏文作为国礼'
            '赠予外宾，被赞"最富东方色彩的民间彩塑"。'
        ),
        'tags': ['惠山泥人', '数字博物馆', '细货', '手捏戏文', '京剧'],
    },
]


def get_or_create_museum_user():
    """获取或创建官方馆藏账号"""
    user = User.query.filter_by(email=MUSEUM_EMAIL).first()
    if user:
        return user
    user = User(username=MUSEUM_USERNAME, email=MUSEUM_EMAIL, password=MUSEUM_PASSWORD)
    db.session.add(user)
    db.session.commit()
    print(f'[+] 已创建官方账号: {MUSEUM_USERNAME} <{MUSEUM_EMAIL}>')
    return user


def seed():
    app = create_app()
    with app.app_context():
        user = get_or_create_museum_user()

        created, skipped = 0, 0
        for ex in EXHIBITS:
            exists = Artwork.query.filter_by(user_id=user.id, title=ex['title']).first()
            if exists:
                skipped += 1
                continue
            artwork = Artwork(
                title=ex['title'],
                description=ex['description'],
                tags=ex['tags'],
                thumbnail=f'{IMAGE_BASE}/{ex["image"]}',
                is_public=True,
                is_ai_generated=False,
                license_type='all-rights-reserved',
            )
            artwork.user_id = user.id
            db.session.add(artwork)
            created += 1

        db.session.commit()
        print(f'[OK] 馆藏导入完成: 新增 {created} 件, 跳过 {skipped} 件 (幂等)')
        print(f'     所属账号: {MUSEUM_USERNAME} (id={user.id})')
        print(f'     缩略图基址: {IMAGE_BASE}/')


if __name__ == '__main__':
    seed()
