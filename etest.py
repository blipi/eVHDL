from easyVHDL import *

# Entitat inversor basic
with Entity("INV"):
    INV.Port([
        ["a", IN],
        ["z", OUT]
    ])

# Entitat NOR3
with Entity("NOR3"):
    NOR3.Port([
        ["a", IN],
        ["b", IN],
        ["c", IN],
        ["z", OUT]
    ])

# Entitat pel banc de proves
Entity("Testbench")

# Arquitectura logica de la porta INV     
with Architecture(INV, "logica") as logica:
    with logica.Process((a,)) as process:
        process(z, NOT(a))

# Aquitectura logica de la porta NOR3
with Architecture(NOR3, "logica") as logica:
    with logica.Process((a,b,c)) as process:
        process(z, NOT(OR(OR(a, b), c)))

# Arquitectura "semi" estructural (OR3 amb portes) de la porta NOR3
with Architecture(NOR3, "estructural") as estructural:
    cINV = Component(INV.logica)
    estructural.Signal([["out_or"]])
    
    with estructural.Process((a,b,c)) as process:
        process(out_or, OR(OR(a, b), c))
        process(z, cINV.z(out_or))


# Arquitectures del banc de proves
with Architecture(Testbench, "test_nor_l") as test_nor_l:
    cNOR3 = Component(NOR3.logica)
    test_nor_l.Signal([["a,b,c,z"]])
    
    with test_nor_l.Process() as process:
        process.wait(50)
        process(a, 1)
        process.wait(50)
        process(b, 0)
        process(a, 0)
        process.wait(50)
        process(c, 1)

    with test_nor_l.Process((a,b,c)) as process:
        process(z, cNOR3.z(a, b, c))

with Architecture(Testbench, "test_nor_e") as test_nor_e:
    cNOR3 = Component(NOR3.estructural)
    test_nor_e.Signal([["a,b,c,z"]])
    
    with test_nor_e.Process() as process:
        process.wait(50)
        process(a, 1)
        process.wait(50)
        process(b, 0)
        process(a, 0)
        process.wait(50)
        process(c, 1)

    with test_nor_e.Process((a,b,c)) as process:
        process(z, cNOR3.z(a, b, c))

Work().Watch(test_nor_l.a, test_nor_l.b, test_nor_l.c, test_nor_l.z)
Work().Run(Testbench.test_nor_l, 200)

Work().Watch(test_nor_e.a, test_nor_e.b, test_nor_e.c, test_nor_e.z)
Work().Run(Testbench.test_nor_e, 200)
