"""
P-METHOD-1 Backfill DELETE — Step 1 of 4.
Deletes 679 duplicate rows. Uses psycopg2 for RETURNING confirmation.
DO NOT run automatically — requires explicit user approval.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
import psycopg2

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise SystemExit("DATABASE_URL must be set")

# The 679 approved delete IDs
DELETE_IDS = [
    1, 11, 12, 38, 43, 44, 46, 47, 49, 54,
    57, 60, 62, 64, 71, 75, 76, 84, 92, 93,
    99, 100, 103, 109, 111, 119, 120, 121, 125, 128,
    130, 131, 134, 137, 138, 139, 144, 147, 152, 159,
    161, 162, 168, 172, 173, 174, 175, 176, 177, 178,
    179, 180, 181, 183, 185, 186, 188, 189, 190, 191,
    192, 193, 194, 195, 196, 197, 198, 199, 200, 201,
    202, 203, 204, 205, 206, 208, 209, 210, 211, 212,
    213, 214, 216, 217, 218, 219, 220, 221, 222, 225,
    227, 228, 229, 231, 232, 233, 234, 235, 238, 239,
    240, 242, 245, 246, 247, 248, 249, 250, 251, 253,
    254, 255, 257, 258, 259, 260, 261, 262, 263, 264,
    265, 266, 267, 268, 269, 270, 271, 272, 273, 274,
    275, 277, 279, 280, 281, 282, 283, 284, 285, 286,
    287, 289, 290, 291, 292, 293, 294, 297, 300, 301,
    302, 303, 305, 308, 309, 311, 312, 313, 314, 315,
    316, 317, 319, 323, 324, 326, 329, 330, 331, 332,
    337, 338, 339, 340, 342, 343, 344, 347, 349, 351,
    352, 356, 359, 360, 361, 362, 363, 364, 368, 369,
    370, 371, 372, 374, 378, 379, 381, 382, 384, 385,
    386, 387, 389, 390, 391, 393, 395, 396, 397, 398,
    399, 400, 402, 404, 405, 407, 411, 412, 413, 414,
    415, 416, 418, 419, 420, 421, 422, 423, 424, 425,
    429, 432, 433, 434, 435, 436, 440, 441, 442, 443,
    445, 446, 447, 448, 450, 451, 452, 454, 455, 456,
    457, 459, 460, 461, 462, 463, 464, 466, 467, 468,
    469, 470, 471, 472, 473, 474, 475, 476, 477, 478,
    480, 482, 483, 484, 485, 486, 487, 489, 490, 492,
    493, 494, 496, 497, 498, 499, 500, 501, 503, 504,
    505, 506, 509, 510, 511, 512, 513, 514, 516, 517,
    518, 520, 521, 522, 523, 524, 525, 526, 527, 529,
    530, 531, 532, 533, 534, 535, 536, 537, 538, 539,
    540, 541, 542, 543, 545, 546, 547, 548, 550, 554,
    556, 557, 558, 559, 563, 564, 565, 566, 568, 569,
    570, 571, 574, 575, 576, 577, 578, 579, 580, 582,
    583, 584, 585, 586, 587, 588, 589, 590, 591, 592,
    593, 594, 595, 596, 597, 599, 600, 601, 602, 603,
    605, 606, 607, 608, 609, 610, 611, 612, 614, 615,
    616, 617, 618, 619, 620, 622, 623, 624, 625, 626,
    627, 628, 630, 631, 632, 633, 634, 635, 636, 637,
    638, 639, 640, 641, 642, 643, 644, 645, 646, 647,
    648, 649, 650, 652, 653, 654, 655, 656, 658, 659,
    660, 661, 662, 663, 664, 665, 666, 667, 669, 670,
    671, 672, 673, 674, 675, 676, 677, 678, 679, 680,
    681, 682, 683, 684, 686, 688, 689, 690, 691, 692,
    693, 695, 697, 698, 699, 700, 701, 702, 703, 704,
    705, 706, 707, 708, 709, 710, 712, 713, 714, 715,
    716, 717, 719, 720, 721, 722, 723, 724, 725, 726,
    727, 728, 729, 730, 731, 732, 733, 734, 735, 736,
    737, 738, 739, 740, 741, 742, 743, 744, 745, 746,
    747, 748, 749, 751, 752, 753, 754, 755, 759, 761,
    762, 764, 765, 766, 767, 768, 769, 770, 771, 773,
    774, 775, 776, 777, 778, 780, 783, 784, 785, 786,
    787, 789, 792, 793, 794, 795, 796, 800, 803, 804,
    806, 808, 809, 811, 812, 813, 814, 815, 816, 817,
    818, 821, 822, 824, 825, 826, 827, 829, 830, 831,
    832, 833, 835, 837, 839, 840, 841, 842, 843, 845,
    846, 847, 848, 849, 851, 852, 853, 854, 855, 856,
    857, 858, 859, 860, 861, 866, 867, 868, 871, 872,
    873, 874, 876, 877, 878, 881, 882, 883, 884, 885,
    888, 890, 891, 893, 894, 895, 898, 901, 904, 905,
    906, 909, 910, 911, 912, 915, 916, 917, 918, 919,
    920, 921, 922, 924, 926, 928, 929, 930, 932, 933,
    935, 937, 938, 941, 943, 947, 948, 949, 950, 951,
    952, 953, 955, 957, 958, 959, 962, 963, 965, 966,
    968, 969, 970, 971, 972, 973, 974, 975, 976, 978,
    979, 981, 982, 983, 984, 985, 986, 993, 994, 999,
    1000, 1001, 1002, 1003, 1004, 1005, 1010, 1013, 1017,
]

assert len(DELETE_IDS) == 679, f"Expected 679 IDs, got {len(DELETE_IDS)}"
assert len(set(DELETE_IDS)) == 679, f"Duplicate IDs in list"

print(f"DELETE target: {len(DELETE_IDS)} rows")
print(f"Connecting to production database...")

conn = psycopg2.connect(DB_URL)
conn.autocommit = False
cur = conn.cursor()

try:
    # Pre-check: count rows that actually exist
    placeholders = ",".join(["%s"] * len(DELETE_IDS))
    cur.execute(f"SELECT COUNT(*) FROM trends WHERE id IN ({placeholders})", DELETE_IDS)
    existing = cur.fetchone()[0]
    print(f"Pre-check: {existing} of {len(DELETE_IDS)} target IDs exist in trends table")
    if existing != len(DELETE_IDS):
        missing = len(DELETE_IDS) - existing
        print(f"WARNING: {missing} IDs do not exist — will delete fewer than expected")

    # Execute DELETE with RETURNING
    cur.execute(f"DELETE FROM trends WHERE id IN ({placeholders}) RETURNING id", DELETE_IDS)
    deleted_ids = [row[0] for row in cur.fetchall()]
    deleted_count = len(deleted_ids)

    print(f"\nDELETE executed: {deleted_count} rows deleted")

    # Post-check: count remaining rows
    cur.execute("SELECT COUNT(*) FROM trends")
    remaining = cur.fetchone()[0]

    # Verify cascade: check trend_snapshots count
    cur.execute("SELECT COUNT(*) FROM trend_snapshots")
    snaps_remaining = cur.fetchone()[0]

    print(f"Remaining trends rows: {remaining}")
    print(f"Remaining trend_snapshots rows: {snaps_remaining}")

    # Commit
    conn.commit()
    print(f"\nCOMMITTED successfully")

    # Final verification
    cur.execute("SELECT COUNT(*) FROM trends")
    final_remaining = cur.fetchone()[0]
    print(f"\n=== FINAL STATE ===")
    print(f"Trends remaining: {final_remaining} (expected: 321)")
    print(f"Verification: {'PASS' if final_remaining == 321 else 'FAIL'}")

    # Check for any NULL audio_ids or duplicates
    cur.execute("SELECT COUNT(*) FROM trends WHERE audio_id IS NULL")
    null_aids = cur.fetchone()[0]
    cur.execute("SELECT audio_id, COUNT(*) as cnt FROM trends GROUP BY audio_id HAVING COUNT(*) > 1")
    dups = cur.fetchall()
    print(f"NULL audio_ids: {null_aids}")
    print(f"Remaining duplicate groups: {len(dups)}")
    if dups:
        for aid, cnt in dups[:5]:
            print(f"  audio_id={aid}: {cnt} rows")

except Exception as e:
    conn.rollback()
    print(f"\nERROR: {e}")
    print(f"ROLLED BACK — no changes made")
    raise
finally:
    cur.close()
    conn.close()
