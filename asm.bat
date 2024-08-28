@echo off
%USERPROFILE%\.platformio\packages\toolchain-atmelavr\bin\avr-objdump.exe -z -d -S --demangle .pio\build\uno\firmware.elf > firmware.lst
pause