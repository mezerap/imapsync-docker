# Převzaté součásti

Vlastní obal je pod MIT licencí v kořenovém LICENSE. Tato licence nemění
podmínky níže uvedených součástí. Celý patches/IMAPClient.pm včetně místních
úprav zůstává pod původními podmínkami; samostatné oznámení je v
[patches/LICENSE](patches/LICENSE).

## Mail::IMAPClient 3.43

`patches/IMAPClient.pm` je upravená kopie modulu Mail::IMAPClient 3.43
z používaného imapsync Docker image. Nejde o původní vlastní implementaci.

Původní autorské oznámení:

```text
Copyright (C) 1999-2003 The Kernen Group, Inc.
Copyright (C) 2007-2009 Mark Overmeer
Copyright (C) 2010-2021 Phil Pearl (Lobbes)
All rights reserved.
```

Podle dokumentace modulu se knihovna distribuuje a upravuje za stejných
podmínek jako Perl 5.8.0 nebo novější Perl 5; viz původní podmínky a vyloučení
záruk v [dokumentaci verze 3.43](https://metacpan.org/release/PLOBBES/Mail-IMAPClient-3.43/view/lib/Mail/IMAPClient.pod#COPYRIGHT-AND-LICENSE).
Zdrojový projekt: [plobbes/mail-imapclient](https://github.com/plobbes/mail-imapclient).

Místní změny v `append_string`:

- Před odesláním se příkaz převádí na bajtový řetězec pomocí
  `utf8::downgrade`, aby Unicode označení názvu složky nezměnilo bajty e-mailu
  a délku IMAP literal dat. Neplatné široké znaky vyvolají chybu.
- `doretry => 0` zabraňuje automatickému opakování nejistého APPEND;
  další synchronizace má nejprve znovu porovnat obsah schránek.

Změny jsou ověřené regresí v `tests/append-octets.t` a používaný image je
připnutý v `docker-compose.yml`.

## Imapsync a Docker image

Samotný program není v tomto repozitáři znovu distribuován; Compose používá
image `gilleslamiral/imapsync`. Dokumentace a podmínky jsou dostupné na
[webu autora](https://imapsync.lamiral.info/) a
[Docker Hubu](https://hub.docker.com/r/gilleslamiral/imapsync/).


## Python a standardní knihovna

Obal nepřidává externí Python balíčky přes pip. Python a jeho standardní
knihovna používají PSF License Version 2 a oznámení případných začleněných
součástí; viz [oficiální licence Pythonu](https://docs.python.org/3/license.html).
Interpreter se tímto repozitářem znovu nedistribuuje.

## Perl a imapsync

Perl nabízí volbu Artistic License nebo GPL verze 1 či novější; viz
[oficiální podmínky Perlu](https://dev.perl.org/licenses/).
Samotný imapsync používá [NO LIMIT PUBLIC LICENSE](https://imapsync.lamiral.info/LICENSE).
Tyto podmínky se nenahrazují MIT licencí našeho obalu.

## Ostatní obsah image

Docker image obsahuje také systémové a Perl závislosti s jejich vlastními
podmínkami. Zdejší přehled není úplným soupisem všech balíčků image ani jeho
licencí. Repozitář odkazuje na existující image pomocí Compose; nevydává vlastní
přebalený image. Při případném vydávání vlastního image je nutné zohlednit
podmínky jeho jednotlivých součástí samostatně.
