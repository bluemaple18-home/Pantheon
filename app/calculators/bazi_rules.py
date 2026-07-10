from __future__ import annotations


HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
ZODIACS = {
    "子": "鼠",
    "丑": "牛",
    "寅": "虎",
    "卯": "兔",
    "辰": "龍",
    "巳": "蛇",
    "午": "馬",
    "未": "羊",
    "申": "猴",
    "酉": "雞",
    "戌": "狗",
    "亥": "豬",
}
STEM_POLARITY = {
    "甲": "yang",
    "乙": "yin",
    "丙": "yang",
    "丁": "yin",
    "戊": "yang",
    "己": "yin",
    "庚": "yang",
    "辛": "yin",
    "壬": "yang",
    "癸": "yin",
}
STEM_ELEMENTS = {
    "甲": "木",
    "乙": "木",
    "丙": "火",
    "丁": "火",
    "戊": "土",
    "己": "土",
    "庚": "金",
    "辛": "金",
    "壬": "水",
    "癸": "水",
}
BRANCH_ELEMENTS = {
    "子": "水",
    "丑": "土",
    "寅": "木",
    "卯": "木",
    "辰": "土",
    "巳": "火",
    "午": "火",
    "未": "土",
    "申": "金",
    "酉": "金",
    "戌": "土",
    "亥": "水",
}
HIDDEN_STEMS = {
    "子": [{"stem": "癸", "role": "main", "weight": 100}],
    "丑": [
        {"stem": "己", "role": "main", "weight": 60},
        {"stem": "癸", "role": "middle", "weight": 30},
        {"stem": "辛", "role": "residual", "weight": 10},
    ],
    "寅": [
        {"stem": "甲", "role": "main", "weight": 60},
        {"stem": "丙", "role": "middle", "weight": 30},
        {"stem": "戊", "role": "residual", "weight": 10},
    ],
    "卯": [{"stem": "乙", "role": "main", "weight": 100}],
    "辰": [
        {"stem": "戊", "role": "main", "weight": 60},
        {"stem": "乙", "role": "middle", "weight": 30},
        {"stem": "癸", "role": "residual", "weight": 10},
    ],
    "巳": [
        {"stem": "丙", "role": "main", "weight": 60},
        {"stem": "戊", "role": "middle", "weight": 30},
        {"stem": "庚", "role": "residual", "weight": 10},
    ],
    "午": [
        {"stem": "丁", "role": "main", "weight": 70},
        {"stem": "己", "role": "middle", "weight": 30},
    ],
    "未": [
        {"stem": "己", "role": "main", "weight": 60},
        {"stem": "丁", "role": "middle", "weight": 30},
        {"stem": "乙", "role": "residual", "weight": 10},
    ],
    "申": [
        {"stem": "庚", "role": "main", "weight": 60},
        {"stem": "壬", "role": "middle", "weight": 30},
        {"stem": "戊", "role": "residual", "weight": 10},
    ],
    "酉": [{"stem": "辛", "role": "main", "weight": 100}],
    "戌": [
        {"stem": "戊", "role": "main", "weight": 60},
        {"stem": "辛", "role": "middle", "weight": 30},
        {"stem": "丁", "role": "residual", "weight": 10},
    ],
    "亥": [
        {"stem": "壬", "role": "main", "weight": 70},
        {"stem": "甲", "role": "middle", "weight": 30},
    ],
}
ELEMENT_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
STEM_COMBINES = {"甲": "己", "乙": "庚", "丙": "辛", "丁": "壬", "戊": "癸"}
STEM_CLASHES = {"甲": "庚", "乙": "辛", "丙": "壬", "丁": "癸"}
BRANCH_CLASHES = {"子": "午", "丑": "未", "寅": "申", "卯": "酉", "辰": "戌", "巳": "亥"}
BRANCH_HARMONIES = {"子": "丑", "寅": "亥", "卯": "戌", "辰": "酉", "巳": "申", "午": "未"}
