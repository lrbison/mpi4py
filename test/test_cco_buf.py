from mpi4py import MPI
import mpiunittest as unittest
import arrayimpl

def maxvalue(a):
    try:
        typecode = a.typecode
    except AttributeError:
        typecode = a.dtype.char
    if typecode == ('f'):
        return 1e30
    elif typecode == ('d'):
        return 1e300
    else:
        return 2 ** (a.itemsize * 7) - 1


class TestCCOBufBase(object):

    COMM = MPI.COMM_NULL

    def testBarrier(self):
        self.COMM.Barrier()

    def testBcast(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for root in range(size):
                    if rank == root:
                        buf = array(root, typecode, root)
                    else:
                        buf = array(  -1, typecode, root)
                    self.COMM.Bcast(buf.as_mpi(), root=root)
                    for value in buf:
                        self.assertEqual(value, root)

    def testGather(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for root in range(size):
                    sbuf = array(root, typecode, root+1)
                    if rank == root:
                        rbuf = array(-1, typecode, (size,root+1))
                    else:
                        rbuf = array([], typecode)
                    self.COMM.Gather(sbuf.as_mpi(), rbuf.as_mpi(),
                                     root=root)
                    if rank == root:
                        for value in rbuf.flat:
                            self.assertEqual(value, root)

    def testScatter(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for root in range(size):
                    rbuf = array(-1, typecode, size)
                    if rank == root:
                        sbuf = array(root, typecode, (size, size))
                    else:
                        sbuf = array([], typecode)
                    self.COMM.Scatter(sbuf.as_mpi(), rbuf.as_mpi(),
                                      root=root)
                    for value in rbuf:
                        self.assertEqual(value, root)

    def testAllgather(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for root in range(size):
                    sbuf = array(root, typecode, root+1)
                    rbuf = array(  -1, typecode, (size, root+1))
                    self.COMM.Allgather(sbuf.as_mpi(), rbuf.as_mpi())
                    for value in rbuf.flat:
                        self.assertEqual(value, root)

    def testAlltoall(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for root in range(size):
                    sbuf = array(root, typecode, (size, root+1))
                    rbuf = array(  -1, typecode, (size, root+1))
                    self.COMM.Alltoall(sbuf.as_mpi(), rbuf.as_mpi_c(root+1))
                    for value in rbuf.flat:
                        self.assertEqual(value, root)

    def assertAlmostEqual(self, first, second):
        num = float(float(second-first))
        den = float(second+first)/2 or 1.0
        if (abs(num/den) > 1e-2):
            raise self.failureException('%r != %r' % (first, second))

    def testReduce(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for root in range(size):
                    for op in (MPI.SUM, MPI.PROD, MPI.MAX, MPI.MIN):
                        sbuf = array(range(size), typecode)
                        rbuf = array(-1, typecode, size)
                        self.COMM.Reduce(sbuf.as_mpi(),
                                         rbuf.as_mpi(),
                                         op, root)
                        max_val = maxvalue(rbuf)
                        for i, value in enumerate(rbuf):
                            if rank != root:
                                self.assertEqual(value, -1)
                                continue
                            if op == MPI.SUM:
                                if (i * size) < max_val:
                                    self.assertAlmostEqual(value, i*size)
                            elif op == MPI.PROD:
                                if (i ** size) < max_val:
                                    self.assertAlmostEqual(value, i**size)
                            elif op == MPI.MAX:
                                self.assertEqual(value, i)
                            elif op == MPI.MIN:
                                self.assertEqual(value, i)

    def testAllreduce(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for op in (MPI.SUM, MPI.MAX, MPI.MIN, MPI.PROD):
                    sbuf = array(range(size), typecode)
                    rbuf = array(0, typecode, size)
                    self.COMM.Allreduce(sbuf.as_mpi(),
                                        rbuf.as_mpi(),
                                        op)
                    max_val = maxvalue(rbuf)
                    for i, value in enumerate(rbuf):
                        if op == MPI.SUM:
                            if (i * size) < max_val:
                                self.assertAlmostEqual(value, i*size)
                        elif op == MPI.PROD:
                            if (i ** size) < max_val:
                                self.assertAlmostEqual(value, i**size)
                        elif op == MPI.MAX:
                            self.assertEqual(value, i)
                        elif op == MPI.MIN:
                            self.assertEqual(value, i)


    def testScan(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        # --
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for op in (MPI.SUM, MPI.PROD, MPI.MAX, MPI.MIN):
                    sbuf = array(range(size), typecode)
                    rbuf = array(0, typecode, size)
                    self.COMM.Scan(sbuf.as_mpi(),
                                   rbuf.as_mpi(),
                                   op)
                    max_val = maxvalue(rbuf)
                    for i, value in enumerate(rbuf):
                        if op == MPI.SUM:
                            if (i * (rank + 1)) < max_val:
                                self.assertAlmostEqual(value, i * (rank + 1))
                        elif op == MPI.PROD:
                            if (i ** (rank + 1)) < max_val:
                                self.assertAlmostEqual(value, i ** (rank + 1))
                        elif op == MPI.MAX:
                            self.assertEqual(value, i)
                        elif op == MPI.MIN:
                            self.assertEqual(value, i)

    def testExscan(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for op in (MPI.SUM, MPI.PROD, MPI.MAX, MPI.MIN):
                    sbuf = array(range(size), typecode)
                    rbuf = array(0, typecode, size)
                    try:
                        self.COMM.Exscan(sbuf.as_mpi(),
                                         rbuf.as_mpi(),
                                         op)
                    except NotImplementedError:
                        return
                    if rank == 1:
                        for i, value in enumerate(rbuf):
                            self.assertEqual(value, i)
                    elif rank > 1:
                        max_val = maxvalue(rbuf)
                        for i, value in enumerate(rbuf):
                            if op == MPI.SUM:
                                if (i * rank) < max_val:
                                    self.assertAlmostEqual(value, i * rank)
                            elif op == MPI.PROD:
                                if (i ** rank) < max_val:
                                    self.assertAlmostEqual(value, i ** rank)
                            elif op == MPI.MAX:
                                self.assertEqual(value, i)
                            elif op == MPI.MIN:
                                self.assertEqual(value, i)


    def testBcastTypeIndexed(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode, datatype in arrayimpl.TypeMap.items():
                for root in range(size):
                    #
                    if rank == root:
                        buf = array(range(10), typecode)
                    else:
                        buf = array(-1, typecode, 10)
                    indices = range(0, len(buf), 2)
                    newtype = datatype.Create_indexed_block(1, indices)
                    newtype.Commit()
                    newbuf = (buf, 1, newtype)
                    self.COMM.Bcast(newbuf, root=root)
                    newtype.Free()
                    if rank != root:
                        for i, value in enumerate(buf):
                            if (i % 2):
                                self.assertEqual(value, -1)
                            else:
                                self.assertEqual(value, i)

                    #
                    if rank == root:
                        buf = array(range(10), typecode)
                    else:
                        buf = array(-1, typecode, 10)
                    indices = range(1, len(buf), 2)
                    newtype = datatype.Create_indexed_block(1, indices)
                    newtype.Commit()
                    newbuf = (buf, 1, newtype)
                    self.COMM.Bcast(newbuf, root)
                    newtype.Free()
                    if rank != root:
                        for i, value in enumerate(buf):
                            if not (i % 2):
                                self.assertEqual(value, -1)
                            else:
                                self.assertEqual(value, i)


class TestCCOBufInplaceBase(object):

    def testGather(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for root in range(size):
                    count = root+3
                    if rank == root:
                        sbuf = MPI.IN_PLACE
                        buf = array(-1, typecode, (size, count))
                        buf.flat[(rank*count):((rank+1)*count)] = array(root, typecode, count)
                        rbuf = buf.as_mpi()
                    else:
                        buf = array(root, typecode, count)
                        sbuf = buf.as_mpi()
                        rbuf = None
                    try:
                        self.COMM.Gather(sbuf, rbuf, root=root)
                    except NotImplementedError:
                        return
                    for value in buf.flat:
                        self.assertEqual(value, root)

    def testScatter(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for root in range(size):
                    for count in range(1, 10):
                        if rank == root:
                            buf = array(root, typecode, (size, count))
                            sbuf = buf.as_mpi()
                            rbuf = MPI.IN_PLACE
                        else:
                            buf = array(-1, typecode, count)
                            sbuf = None
                            rbuf = buf.as_mpi()
                        try:
                            self.COMM.Scatter(sbuf, rbuf, root=root)
                        except NotImplementedError:
                            return
                        for value in buf.flat:
                            self.assertEqual(value, root)

    def testAllgather(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for count in range(1, 10):
                    buf = array(-1, typecode, (size, count))
                    buf.flat[(rank*count):((rank+1)*count)] = array(count, typecode, count)
                    try:
                        self.COMM.Allgather(MPI.IN_PLACE, buf.as_mpi())
                    except NotImplementedError:
                        return
                    for value in buf.flat:
                        self.assertEqual(value, count)

    def testReduce(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for root in range(size):
                    for op in (MPI.SUM, MPI.PROD, MPI.MAX, MPI.MIN):
                        count = size
                        if rank == root:
                            buf  = array(range(size), typecode)
                            sbuf = MPI.IN_PLACE
                            rbuf = buf.as_mpi()
                        else:
                            buf  = array(range(size), typecode)
                            buf2 = array(range(size), typecode)
                            sbuf = buf.as_mpi()
                            rbuf = buf2.as_mpi()
                        try:
                            self.COMM.Reduce(sbuf, rbuf, op, root)
                        except NotImplementedError:
                            return
                        if rank == root:
                            max_val = maxvalue(buf)
                            for i, value in enumerate(buf):
                                if op == MPI.SUM:
                                    if (i * size) < max_val:
                                        self.assertAlmostEqual(value, i*size)
                                elif op == MPI.PROD:
                                    if (i ** size) < max_val:
                                        self.assertAlmostEqual(value, i**size)
                                elif op == MPI.MAX:
                                    self.assertEqual(value, i)
                                elif op == MPI.MIN:
                                    self.assertEqual(value, i)

    def testAllreduce(self):
        size = self.COMM.Get_size()
        rank = self.COMM.Get_rank()
        for array in arrayimpl.ArrayTypes:
            for typecode in arrayimpl.TypeMap:
                for op in (MPI.SUM, MPI.MAX, MPI.MIN, MPI.PROD):
                    buf = array(range(size), typecode)
                    sbuf = MPI.IN_PLACE
                    rbuf = buf.as_mpi()
                    self.COMM.Allreduce(sbuf, rbuf, op)
                    max_val = maxvalue(buf)
                    for i, value in enumerate(buf):
                        if op == MPI.SUM:
                            if (i * size) < max_val:
                                self.assertAlmostEqual(value, i*size)
                        elif op == MPI.PROD:
                            if (i ** size) < max_val:
                                self.assertAlmostEqual(value, i**size)
                        elif op == MPI.MAX:
                            self.assertEqual(value, i)
                        elif op == MPI.MIN:
                            self.assertEqual(value, i)


class TestCCOBufSelf(TestCCOBufBase, unittest.TestCase):
    COMM = MPI.COMM_SELF

class TestCCOBufWorld(TestCCOBufBase, unittest.TestCase):
    COMM = MPI.COMM_WORLD

class TestCCOBufInplaceSelf(TestCCOBufInplaceBase, unittest.TestCase):
    COMM = MPI.COMM_SELF

class TestCCOBufInplaceWorld(TestCCOBufInplaceBase, unittest.TestCase):
    COMM = MPI.COMM_WORLD

class TestCCOBufSelfDup(TestCCOBufBase, unittest.TestCase):
    def setUp(self):
        self.COMM = MPI.COMM_SELF.Dup()
    def tearDown(self):
        self.COMM.Free()

class TestCCOBufWorldDup(TestCCOBufBase, unittest.TestCase):
    def setUp(self):
        self.COMM = MPI.COMM_WORLD.Dup()
    def tearDown(self):
        self.COMM.Free()


_name, _version = MPI.get_vendor()
if _name == 'MPICH1':
    del TestCCOBufInplaceBase
    del TestCCOBufInplaceSelf
    del TestCCOBufInplaceWorld


if __name__ == '__main__':
    unittest.main()
