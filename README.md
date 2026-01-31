1 2 3

1. Am luat pseudocodul din cerinta pentru partea cu learning. Nimic de adaugat aici.

Explicatie ex1.jpg:
    Se vede in ss cum am trimis de la host0 la host2. In terminalul host 2 este trecut si numele meu + grupa. Se observa si un window de wireshark cu host2 unde sunt ping request si reply, adica a ajuns packetula acolo, iar in host0 terminal se vad cum au si ajuns aceste reply uri.

2. M-am luat dupa cerinta pentru vlan si am implementat citire a config file-ului, creare logica trunk, verificare vlan + verificare vlan extins. Aici mari dificultati nu am intalnit, decat ca am uitat sa fac vlanul extins prima data (forgor).
   Pe scurt, daca primesc un pachet pe un trunk creez si o varianta non trunk fara acel vlan tag, else daca primesc de pe un acces fac si o varianta cu acel tag, si le trimit pe ambele in functie de interfata destinatie, ori vlan ori trunk.

Explicatie ex2.jpg:
    Se vede in ss cum am incercat sa trm de la host0 la host3, dar au vlan diferit, deci nu ajunge. Dar se vede in wireshark cum ajunge packetul in switchu 1 si e tagged (are protocol 8200)

3. Am implementat intai functia care trimite HDPU uri, dau sleep(1) dupa fiecare loop in care trimit la toti in vecinii (acces si trunks). Cand le citescc dau continue.
    Dupa am implementat fuctia de trimitr PPDU uri, am luat toate valorile alea din cerinta/standardu 802.1D - 2004. Sper ca sunt corecte (port ochelari => nu vad si ma uit la short pe yt => nu am attention span). Pe astea le trimit doar pe switch uri.
    Logica lor este:
    Verific root_id ul, daca e altul, fac interfata aia forwarding (de pe care a venit) si restu blocked. Daca sunt egale verific distantele, else bridge id urile. Daca sunt in root fac toate porturile forwarding. Apoi am adaugat in logica de la 2, verificari:
        daca primesc pe port blocat arunc si verific sa fie un port pornit si cand vreau sa trimit. Ca sa mearga in cam table bag doar daca e deschis acel port. De asemenea PPDU urile le trimit in interval de 2 secunde (hello time ul din standard).

    Aici cele mai multe dificultati le am avut ca nu am citit bine valorile specifice si aveam probleme. Dar sper ca le am rezolvat pe toate

Explicatie ex3.jpg:
    Aici doar am pornit switchurile si se vede un packet ppdu cu tot cu continutul. Se vad si packete bogus, care sunt hello urile.
    Nu prea am ce sa mentionez decat ca se observa ca e corect ppdu ul

Legat de pptx: Nu sunt un artist si nici nu mai am timp e 23:11, dar zic ca se intelege cat de cat.# RL-Custom-Switch
