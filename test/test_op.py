from mpi4py import MPI
import mpiunittest as unittest

try:
    import array
except ImportError:
    array = None

def asarray(typecode, data):
    tobytes = lambda s: memoryview(s).tobytes()
    frombytes = array.array.frombytes
    a = array.array(typecode, [])
    frombytes(a, tobytes(data))
    return a

def mysum_obj(a, b):
    for i in range(len(a)):
        b[i] = a[i] + b[i]
    return b

def mysum_buf(a, b, dt):
    assert dt == MPI.INT
    assert len(a) == len(b)
    b[:] = mysum_obj(asarray('i', a), asarray('i', b))

def mysum(ba, bb, dt):
    if dt is None:
        return mysum_obj(ba, bb)
    else:
        return mysum_buf(ba, bb, dt)


class TestOp(unittest.TestCase):

    def testConstructor(self):
        op = MPI.Op()
        self.assertFalse(op)
        self.assertEqual(op, MPI.OP_NULL)

    @unittest.skipIf(array is None, 'array')
    def testCreate(self):
        for comm in [MPI.COMM_SELF, MPI.COMM_WORLD]:
            for commute in [True, False]:
                for N in range(4):
                    myop = MPI.Op.Create(mysum, commute)
                    self.assertFalse(myop.is_predefined)
                    try:
                        size = comm.Get_size()
                        rank = comm.Get_rank()
                        a = array.array('i', [i*(rank+1) for i in range(N)])
                        b = array.array('i', [0]*len(a))
                        comm.Allreduce([a, MPI.INT], [b, MPI.INT], myop)
                        scale = sum(range(1,size+1))
                        for i in range(N):
                            self.assertEqual(b[i], scale*i)
                        res = myop(a, b)
                        self.assertIs(res, b)
                        for i in range(N):
                            self.assertEqual(b[i], a[i]+scale*i)
                        myop2 = MPI.Op(myop)
                        a = array.array('i', [1]*N)
                        b = array.array('i', [2]*N)
                        res = myop2(a, b)
                        self.assertIs(res, b)
                        for i in range(N):
                            self.assertEqual(b[i], 3)
                        myop2 = None
                    finally:
                        myop.Free()

    def testCreateMany(self):
        N = 32 # max user-defined operations
        #
        ops = []
        for i in range(N):
            o = MPI.Op.Create(mysum)
            ops.append(o)
        for o in ops: o.Free() # cleanup
        # another round
        ops = []
        for i in range(N):
            o = MPI.Op.Create(mysum)
            ops.append(o)
        for o in ops: o.Free() # cleanup

    def _test_call(self, op, args, res):
        self.assertEqual(op(*args), res)
        self.assertEqual(MPI.Op(op)(*args), res)

    def testCall(self):
        self.assertRaises(TypeError, MPI.OP_NULL)
        self.assertRaises(TypeError, MPI.OP_NULL, None)
        self.assertRaises(ValueError, MPI.OP_NULL, None, None)
        self._test_call(MPI.MIN,  (2,3), 2)
        self._test_call(MPI.MAX,  (2,3), 3)
        self._test_call(MPI.SUM,  (2,3), 5)
        self._test_call(MPI.PROD, (2,3), 6)
        for x in (False, True):
            for y in (False, True):
                self._test_call(MPI.LAND,  (x,y), x and y)
                self._test_call(MPI.LOR,   (x,y), x or  y)
                self._test_call(MPI.LXOR,  (x,y), x ^ y)
        for x in range(5):
            for y in range(5):
                self._test_call(MPI.BAND,  (x,y), x  &  y)
                self._test_call(MPI.BOR,   (x,y), x  |  y)
                self._test_call(MPI.BXOR,  (x,y), x  ^  y)
        if MPI.REPLACE:
            self._test_call(MPI.REPLACE, (2,3), 3)
            self._test_call(MPI.REPLACE, (3,2), 2)
        if MPI.NO_OP:
            self._test_call(MPI.NO_OP, (2,3), 2)
            self._test_call(MPI.NO_OP, (3,2), 3)

    def testMinMax(self):
        x = [1]; y = [1]
        res = MPI.MIN(x, y)
        self.assertEqual(res, x)
        res = MPI.MAX(x, y)
        self.assertEqual(res, x)

    def testMinMaxLoc(self):
        x = [1]; i = [2]; u = [x, i]
        y = [2]; j = [1]; v = [y, j]
        res = MPI.MINLOC(u, v)
        self.assertIs(res[0], x)
        self.assertIs(res[1], i)
        res = MPI.MINLOC(v, u)
        self.assertIs(res[0], x)
        self.assertIs(res[1], i)
        res = MPI.MAXLOC(u, v)
        self.assertIs(res[0], y)
        self.assertIs(res[1], j)
        res = MPI.MAXLOC(v, u)
        self.assertIs(res[0], y)
        self.assertIs(res[1], j)
        #
        x = [1]; i = 0; u = [x, i]
        y = [1]; j = 1; v = [y, j]
        res = MPI.MINLOC(u, v)
        self.assertIs(res[0], x)
        self.assertIs(res[1], i)
        res = MPI.MAXLOC(u, v)
        self.assertIs(res[0], x)
        self.assertIs(res[1], i)
        #
        x = [1]; i = 1; u = [x, i]
        y = [1]; j = 0; v = [y, j]
        res = MPI.MINLOC(u, v)
        self.assertIs(res[0], y)
        self.assertIs(res[1], j)
        res = MPI.MAXLOC(u, v)
        self.assertIs(res[0], y)
        self.assertIs(res[1], j)
        #
        x = [1]; i = [0]; u = [x, i]
        y = [1]; j = [1]; v = [y, j]
        res = MPI.MINLOC(u, v)
        self.assertIs(res[0], x)
        self.assertIs(res[1], i)
        res = MPI.MAXLOC(u, v)
        self.assertIs(res[0], x)
        self.assertIs(res[1], i)
        #
        x = [1]; i = [1]; u = [x, i]
        y = [1]; j = [0]; v = [y, j]
        res = MPI.MINLOC(u, v)
        self.assertIs(res[0], y)
        self.assertIs(res[1], j)
        res = MPI.MAXLOC(u, v)
        self.assertIs(res[0], y)
        self.assertIs(res[1], j)

    @unittest.skipMPI('openmpi(<=1.8.1)')
    def testIsCommutative(self):
        try:
            MPI.SUM.Is_commutative()
        except NotImplementedError:
            self.skipTest('mpi-op-is_commutative')
        ops = [
            MPI.MAX,    MPI.MIN,
            MPI.SUM,    MPI.PROD,
            MPI.LAND,   MPI.BAND,
            MPI.LOR,    MPI.BOR,
            MPI.LXOR,   MPI.BXOR,
            MPI.MAXLOC, MPI.MINLOC,
        ]
        for op in ops:
            flag = op.Is_commutative()
            self.assertEqual(flag, op.is_commutative)
            self.assertTrue(flag)

    @unittest.skipMPI('openmpi(<=1.8.1)')
    @unittest.skipMPI('mpich(==3.4.1)')
    def testIsCommutativeExtra(self):
        try:
            MPI.SUM.Is_commutative()
        except NotImplementedError:
            self.skipTest('mpi-op-is_commutative')
        ops =  [MPI.REPLACE, MPI.NO_OP]
        for op in ops:
            if not op: continue
            flag = op.Is_commutative()
            self.assertEqual(flag, op.is_commutative)
            #self.assertFalse(flag)

    def testIsPredefined(self):
        self.assertTrue(MPI.OP_NULL.is_predefined)
        ops = [MPI.MAX,    MPI.MIN,
               MPI.SUM,    MPI.PROD,
               MPI.LAND,   MPI.BAND,
               MPI.LOR,    MPI.BOR,
               MPI.LXOR,   MPI.BXOR,
               MPI.MAXLOC, MPI.MINLOC,]
        for op in ops:
            self.assertTrue(op.is_predefined)


if __name__ == '__main__':
    unittest.main()
