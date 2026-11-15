import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { VoiceInput, type Recording } from './VoiceInput'

const AUDIO = new Blob(['audio'], { type: 'audio/webm' })

function setup(
  options: {
    transcript?: string | null
    startFails?: boolean
    transcribeFails?: boolean
  } = {},
) {
  const stop = vi.fn(async () => AUDIO)
  const recording: Recording = { stop }
  const startRecording = vi.fn(async () => {
    if (options.startFails) throw new Error('NotAllowedError')
    return recording
  })
  const transcribe = vi.fn(async () => {
    if (options.transcribeFails) throw new Error('fallo')
    return options.transcript === null ? null : { text: options.transcript ?? 'why do I have a headache' }
  })
  const onConfirm = vi.fn()
  render(
    <VoiceInput
      startRecording={startRecording}
      transcribe={transcribe}
      onConfirm={onConfirm}
      notice="Simulated transcript: no voice model is connected yet."
    />,
  )
  return { startRecording, transcribe, onConfirm, stop }
}

async function holdAndRelease(user = userEvent.setup()) {
  const button = screen.getByRole('button', { name: 'Hold to talk' })
  await user.pointer([{ keys: '[MouseLeft>]', target: button }])
  await user.pointer([{ keys: '[/MouseLeft]', target: button }])
}

describe('VoiceInput', () => {
  it('says it is listening while the button is held', async () => {
    setup()
    const user = userEvent.setup()
    const button = screen.getByRole('button', { name: 'Hold to talk' })

    await user.pointer([{ keys: '[MouseLeft>]', target: button }])

    expect(await screen.findByRole('status')).toHaveTextContent('Listening')
  })

  it('shows the transcript as editable text and waits: nothing is sent yet', async () => {
    const { onConfirm } = setup()

    await holdAndRelease()

    const field = await screen.findByLabelText('Transcript (you can correct it)')
    expect(field).toHaveValue('why do I have a headache')
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('says the transcript is simulated when no speech model is connected', async () => {
    setup()

    await holdAndRelease()

    expect(await screen.findByText(/Simulated transcript/)).toBeVisible()
  })

  it('confirms the text the crew corrected, not the original', async () => {
    const { onConfirm } = setup({ transcript: 'por que me duele la caveza' })
    const user = userEvent.setup()

    await holdAndRelease(user)
    const field = await screen.findByLabelText('Transcript (you can correct it)')
    await user.clear(field)
    await user.type(field, 'Why do I have a headache?')
    await user.click(screen.getByRole('button', { name: 'Confirm and ask' }))

    expect(onConfirm).toHaveBeenCalledWith('Why do I have a headache?')
  })

  it('goes back to the start after confirming', async () => {
    setup()
    const user = userEvent.setup()

    await holdAndRelease(user)
    await user.click(await screen.findByRole('button', { name: 'Confirm and ask' }))

    expect(screen.getByRole('button', { name: 'Hold to talk' })).toBeVisible()
    expect(screen.queryByLabelText('Transcript (you can correct it)')).not.toBeInTheDocument()
  })

  it('discards a transcript without sending it', async () => {
    const { onConfirm } = setup()
    const user = userEvent.setup()

    await holdAndRelease(user)
    await user.click(await screen.findByRole('button', { name: 'Discard' }))

    expect(onConfirm).not.toHaveBeenCalled()
    expect(screen.queryByLabelText('Transcript (you can correct it)')).not.toBeInTheDocument()
  })

  it('does not allow confirming an empty text', async () => {
    setup()
    const user = userEvent.setup()

    await holdAndRelease(user)
    await user.clear(await screen.findByLabelText('Transcript (you can correct it)'))

    expect(screen.getByRole('button', { name: 'Confirm and ask' })).toBeDisabled()
  })

  it('works from the keyboard: hold Space to talk', async () => {
    const { startRecording } = setup()
    const user = userEvent.setup()
    screen.getByRole('button', { name: 'Hold to talk' }).focus()

    await user.keyboard('[Space>]')
    expect(await screen.findByRole('status')).toHaveTextContent('Listening')
    await user.keyboard('[/Space]')

    expect(startRecording).toHaveBeenCalledTimes(1)
    expect(await screen.findByLabelText('Transcript (you can correct it)')).toBeVisible()
  })

  it('tells the crew to type when there is no microphone or no permission', async () => {
    setup({ startFails: true })

    await holdAndRelease()

    expect(await screen.findByRole('alert')).toHaveTextContent('type your question')
  })

  it('tells the crew to type when the transcription fails or comes back empty', async () => {
    const failing = setup({ transcribeFails: true })
    await holdAndRelease()
    expect(await screen.findByRole('alert')).toHaveTextContent('type your question')
    expect(failing.onConfirm).not.toHaveBeenCalled()
  })

  it('tells the crew to type when nothing was heard', async () => {
    setup({ transcript: null })

    await holdAndRelease()

    expect(await screen.findByRole('alert')).toHaveTextContent('type your question')
  })
})
