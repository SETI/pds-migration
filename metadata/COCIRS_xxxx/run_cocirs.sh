#!/bin/bash
# PDS_HOLDINGS_DIR=/Volumes/pdsdata/COCIRS/Volumes/pdsdata-raid45/holdings
PDS_HOLDINGS_DIR=$1
METADIR=$PDS_HOLDINGS_DIR/metadata
VOLROOT=$PDS_HOLDINGS_DIR/volumes

TEST_COCIRS=(0405 1002)
# TEST_COCIRS=(0401 0402 0403 0404 0405 0406 0407 0408 0409 0410 0411 0412
# 1001 1002 1003 1004 1005 1006 1007 1008 1009 1010 1011 1012)
COCIRS=(0401 0402 0403 0404 0405 0406 0407 0408 0409 0410 0411 0412
0501 0502 0503 0504 0505 0506 0507 0508 0509 0510 0511 0512
0601 0602 0603 0604 0605 0606 0607 0608 0609 0610 0611 0612
0701 0702 0703 0704 0705 0706 0707 0708 0709 0710 0711 0712
0801 0802 0803 0804 0805 0806 0807 0808 0809 0810 0811 0812
0901 0902 0903 0904 0905 0906 0907 0908 0909 0910 0911 0912
1001 1002 1003 1004 1005 1006 1007 1008 1009 1010 1011 1012
1101 1102 1103 1104 1105 1106 1107 1108 1109 1110 1111 1112
1201 1202 1203 1204 1205 1206 1207 1208 1209 1210 1211 1212
1301 1302 1303 1304 1305 1306 1307 1308 1309 1310 1311 1312
1401 1402 1403 1404 1405 1406 1407 1408 1409 1410 1411 1412
1501 1502 1503 1504 1505 1506 1507 1508 1509 1510 1511 1512
1601 1602 1603 1604 1605 1606 1607 1608 1609 1610 1611 1612
1701 1702 1703 1704 1705 1706 1707 1708 1709)

for vol in "${COCIRS[@]}"; do \
    echo '******' COCIRS_${vol} '******';\
    python generate_cocirs_index_files.py $VOLROOT/COCIRS_${vol:0:1}xxx/COCIRS_${vol}/INDEX/CUBE_EQUI_INDEX.LBL $VOLROOT/COCIRS_${vol:0:1}xxx/COCIRS_${vol} cube_equi_supplemental_index.lbl; \
    python generate_cocirs_index_files.py $VOLROOT/COCIRS_${vol:0:1}xxx/COCIRS_${vol}/INDEX/CUBE_POINT_INDEX.LBL $VOLROOT/COCIRS_${vol:0:1}xxx/COCIRS_${vol} cube_point_supplemental_index.lbl; \
    python generate_cocirs_index_files.py $VOLROOT/COCIRS_${vol:0:1}xxx/COCIRS_${vol}/INDEX/CUBE_RING_INDEX.LBL $VOLROOT/COCIRS_${vol:0:1}xxx/COCIRS_${vol} cube_ring_supplemental_index.lbl; \
done;
