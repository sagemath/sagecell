from ipykernel.comm import Comm

import sys

class SageCellComm(Comm):
    def __init__(self, *args, **kwargs):
        sys._sage_.reset_kernel_timeout(float('inf'))
        super(SageCellComm, self).__init__(*args, **kwargs)

