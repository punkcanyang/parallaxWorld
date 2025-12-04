import { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { MainLayout } from '../components/common';

type WorldSnapshot = Record<string, any>;
type LogEntry = Record<string, any>;
type Character = Record<string, any>;

const api = async (path: string, options?: RequestInit) => {
  const res = await fetch(`/world${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
  });
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
};

export default function PageWorld() {
  const [world, setWorld] = useState<WorldSnapshot | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [chars, setChars] = useState<Character[]>([]);
  const [selected, setSelected] = useState<Character | null>(null);
  const [timeScale, setTimeScale] = useState<number>(1);

  const loadWorld = async () => {
    const data = await api('/world');
    setWorld(data);
    if (typeof data?.time_scale === 'number') {
      setTimeScale(data.time_scale);
    }
  };

  const loadLogs = async () => {
    const data = await api('/logs/tail?limit=30');
    setLogs(data.logs || []);
  };

  const loadChars = async () => {
    const data = await api('/characters');
    setChars(data.characters || []);
  };

  const onStep = async () => {
    await api('/simulate/step', { method: 'POST' });
    await Promise.all([loadWorld(), loadLogs()]);
  };

  const onStart = async () => {
    await api('/simulate/start', { method: 'POST' });
  };

  const onStop = async () => {
    await api('/simulate/stop', { method: 'POST' });
    await loadWorld();
  };

  const onTimeScaleChange = async () => {
    await api('/world/time-scale', { method: 'POST', body: JSON.stringify({ time_scale: timeScale }) });
    await loadWorld();
  };

  useEffect(() => {
    void loadWorld();
    void loadChars();
    void loadLogs();
    const interval = setInterval(() => {
      loadLogs().catch(() => undefined);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const worldInfo = useMemo(() => {
    if (!world) return null;
    return {
      id: world.id,
      name: world.name,
      epoch: world.epoch,
      time_scale: world.time_scale,
      locations: world.locations ? Object.values(world.locations) : [],
    };
  }, [world]);

  return (
    <MainLayout>
      <Stack direction='row' justifyContent='space-between' width='100%' alignItems='center'>
        <Typography variant='h4'>Virtual Town</Typography>
        <Stack direction='row' spacing={1}>
          <Button variant='contained' onClick={onStart}>
            Start
          </Button>
          <Button variant='outlined' onClick={onStop}>
            Stop
          </Button>
          <Button variant='outlined' onClick={onStep}>
            Step
          </Button>
        </Stack>
      </Stack>

      <Divider sx={{ my: 2 }} />

      <Stack direction='row' spacing={3} width='100%' alignItems='flex-start'>
        <Stack spacing={2} flex={1}>
          <Typography variant='h6'>World</Typography>
          {worldInfo ? (
            <Stack spacing={1}>
              <Typography variant='body2'>Name: {worldInfo.name}</Typography>
              <Typography variant='body2'>Epoch: {worldInfo.epoch}</Typography>
              <Typography variant='body2'>Time Scale: {worldInfo.time_scale}</Typography>
              <Stack direction='row' spacing={1} alignItems='center'>
                <TextField
                  label='Time Scale'
                  size='small'
                  type='number'
                  value={timeScale}
                  onChange={(e) => setTimeScale(Number(e.target.value))}
                  sx={{ width: '8rem' }}
                />
                <Button variant='outlined' onClick={onTimeScaleChange}>
                  Update
                </Button>
              </Stack>
              <Typography variant='body2'>Locations: {worldInfo.locations?.length || 0}</Typography>
            </Stack>
          ) : (
            <Typography variant='body2' color='text.secondary'>
              Loading world...
            </Typography>
          )}

          <Divider />

          <Typography variant='h6'>Characters</Typography>
          <List dense>
            {chars.map((c) => (
              <ListItem
                key={c.id}
                secondaryAction={
                  <Button size='small' onClick={() => setSelected(c)}>
                    Details
                  </Button>
                }
              >
                <ListItemText primary={c.name || c.id} secondary={`role: ${c.role || 'n/a'}`} />
              </ListItem>
            ))}
          </List>
        </Stack>

        <Stack spacing={2} flex={1.2}>
          <Typography variant='h6'>Event Feed</Typography>
          <Box
            sx={{
              border: (theme) => `1px solid ${theme.palette.divider}`,
              borderRadius: 2,
              p: 2,
              minHeight: '320px',
              maxHeight: '60vh',
              overflow: 'auto',
            }}
          >
            {logs.length === 0 && (
              <Typography variant='body2' color='text.secondary'>
                No logs yet.
              </Typography>
            )}
            <Stack spacing={1}>
              {logs
                .slice()
                .reverse()
                .map((l, idx) => (
                  <Box key={idx} sx={{ borderBottom: '1px solid rgba(255,255,255,0.05)', pb: 1 }}>
                    <Typography variant='body2' fontWeight='medium'>
                      [{l.tick ?? '-'}] {l.type}
                    </Typography>
                    {l.dialogue && (
                      <Typography variant='body2' color='text.secondary'>
                        {l.dialogue}
                      </Typography>
                    )}
                    {l.effects_applied && (
                      <Typography variant='caption' color='text.secondary'>
                        Effects: {JSON.stringify(l.effects_applied)}
                      </Typography>
                    )}
                  </Box>
                ))}
            </Stack>
          </Box>
        </Stack>
      </Stack>

      <Dialog open={!!selected} onClose={() => setSelected(null)} maxWidth='sm' fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant='h6'>{selected?.name}</Typography>
          <IconButton onClick={() => setSelected(null)}>
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selected ? (
            <Stack spacing={1}>
              <Typography variant='body2'>ID: {selected.id}</Typography>
              <Typography variant='body2'>Role: {selected.role}</Typography>
              <Typography variant='body2'>Age: {selected.age}</Typography>
              <Typography variant='body2'>Location: {selected.location_id || 'n/a'}</Typography>
              <Typography variant='body2'>States: {JSON.stringify(selected.states || {})}</Typography>
              <Typography variant='body2'>Traits: {JSON.stringify(selected.traits || {})}</Typography>
              <Typography variant='body2'>
                Relationships: {JSON.stringify(selected.relationships || {})}
              </Typography>
            </Stack>
          ) : null}
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}

