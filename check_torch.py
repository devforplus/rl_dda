try:
    import torch
    print('torch installed:', torch.__version__)
    import torch.nn
    print('torch.nn imported successfully')
except Exception as e:
    print('torch not installed:', e)
    import traceback
    traceback.print_exc()


