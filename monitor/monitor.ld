/* SPDX-License-Identifier: MIT */

SECTIONS {
	. = 0x83000000 - 0xc0;

	.text : {
		*(.text*);
	}

	.rodata : {
		*(.rodata*);
		*(.data.rel.ro*);
	}
}
