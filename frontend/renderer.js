const React = require('react');
const ReactDOM = require('react-dom');
const { Box, Container, Typography, Paper, Grid, Button, TextField, Switch, FormControlLabel } = require('@mui/material');
const { styled } = require('@mui/material/styles');

const Root = styled('div')(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  minHeight: '100vh',
  backgroundColor: theme.palette.background.default,
}));

const Header = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.primary.contrastText,
}));

const FeatureCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
}));

const App = () => {
  return (
    <Root>
      <Header elevation={3}>
        <Typography variant="h4" component="h1">
          EmailBot - AI Email Assistant
        </Typography>
      </Header>

      <Container maxWidth="lg">
        <Grid container spacing={3}>
          {/* AI-Powered Email Writing */}
          <Grid item xs={12} md={6}>
            <FeatureCard elevation={2}>
              <Typography variant="h6" gutterBottom>
                AI-Powered Email Writing
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Email Draft"
                variant="outlined"
                margin="normal"
              />
              <Button variant="contained" color="primary" sx={{ mt: 2 }}>
                Generate Response
              </Button>
            </FeatureCard>
          </Grid>

          {/* Smart Email Management */}
          <Grid item xs={12} md={6}>
            <FeatureCard elevation={2}>
              <Typography variant="h6" gutterBottom>
                Smart Email Management
              </Typography>
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Auto-send emails"
              />
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Auto-sort into labels"
              />
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="Phishing detection"
              />
              <FormControlLabel
                control={<Switch defaultChecked />}
                label="AI spam filtering"
              />
            </FeatureCard>
          </Grid>

          {/* Actionable Insights */}
          <Grid item xs={12}>
            <FeatureCard elevation={2}>
              <Typography variant="h6" gutterBottom>
                Actionable Insights
              </Typography>
              <TextField
                fullWidth
                multiline
                rows={2}
                label="Custom Prompt"
                variant="outlined"
                margin="normal"
              />
              <Box sx={{ mt: 2 }}>
                <Button variant="outlined" color="primary" sx={{ mr: 2 }}>
                  Review AI Actions
                </Button>
                <Button variant="outlined" color="secondary">
                  Undo Last Action
                </Button>
              </Box>
            </FeatureCard>
          </Grid>
        </Grid>
      </Container>
    </Root>
  );
};

ReactDOM.render(<App />, document.getElementById('root')); 