#include <regdef.h>

	.text
entry:
	.rep 0x400
	nop
	.endr


	li	t1, 'A'
	lui	t0, 0xbf20
loop:	sh	t1, 0x1300(t0)
	b	loop
	nop
