import streamlit as st
import openai
import chess
import chess.svg
import base64
import os
import re

# --- Set OpenAI API key directly (for legacy API) ---
openai.api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Chess vs AI", page_icon="♟️")
st.title("♟️ Chess: Play against OpenAI GPT")
st.caption("You play White. Enter your move in UCI format (e.g. e2e4). The AI (Black) replies using OpenAI GPT.")

def render_svg(board_obj):
    svg = chess.svg.board(board=board_obj, size=400)
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    html = f'<img src="data:image/svg+xml;base64,{b64}"/>'
    st.markdown(html, unsafe_allow_html=True)

# Session state
if "board" not in st.session_state:
    st.session_state.board = chess.Board()
if "history" not in st.session_state:
    st.session_state.history = []
if "game_over" not in st.session_state:
    st.session_state.game_over = False
if "message" not in st.session_state:
    st.session_state.message = ""

def reset_game():
    st.session_state.board = chess.Board()
    st.session_state.history = []
    st.session_state.game_over = False
    st.session_state.message = ""

if st.button("🔄 Reset Game"):
    reset_game()

board = st.session_state.board

# Render the board at the top
render_svg(board)

# Show move history
if st.session_state.history:
    st.markdown("**Move history:**")
    moves_per_row = 5
    move_lines = [
        " ".join(st.session_state.history[i:i + moves_per_row])
        for i in range(0, len(st.session_state.history), moves_per_row)
    ]
    for line in move_lines:
        st.code(line)

def display_game_result(board):
    if board.is_checkmate():
        if board.turn:  # White's turn, so black just mated
            st.error("Checkmate! AI wins!")
        else:
            st.success("Checkmate! You win!")
        return True
    elif board.is_stalemate():
        st.info("Stalemate!")
        return True
    elif board.is_insufficient_material():
        st.info("Draw by insufficient material.")
        return True
    elif board.is_seventyfive_moves():
        st.info("Draw by 75-move rule.")
        return True
    elif board.is_fivefold_repetition():
        st.info("Draw by fivefold repetition.")
        return True
    elif board.is_game_over():
        st.info(f"Game over! Result: {board.result()}")
        return True
    return False

# If game is over, display result and do not allow further input
if display_game_result(board):
    st.session_state.game_over = True
    st.stop()

st.markdown("**Your move (UCI notation, e.g. e2e4):**")
move = st.text_input("Move", key="move_input", max_chars=5)
move = move.strip()

if st.button("Submit Move") and not st.session_state.game_over:
    try:
        chess_move = chess.Move.from_uci(move)
        if chess_move in board.legal_moves:
            board.push(chess_move)
            st.session_state.history.append(move)
        else:
            st.session_state.message = "Illegal move. Please try again."
    except Exception:
        st.session_state.message = "Invalid move format. Use UCI notation (e.g. e2e4)."

    render_svg(board)

    # After player's move, check if game over
    if display_game_result(board):
        st.session_state.game_over = True
    else:
        # AI's turn
        with st.spinner("AI is thinking..."):
            prompt = (
                f"You are a chess AI playing as Black. The current board position is in FEN: {board.fen()}\n"
                "You are a professional chess engine. Always play the objectively best move available according to grandmaster and engine-level chess principles. "
                "Never suggest an illegal move. Only reply with a single legal UCI move for Black (e.g. e7e5), and nothing else. "
                "If there is more than one best move, choose the most challenging for White. "
                "Do not explain your move."
            )
            try:
                for _ in range(6):  # Try up to 6 times to get a legal move
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a professional chess grandmaster and engine. Always output only the best legal move for Black in UCI format and nothing else. Never suggest an illegal move. Only reply with a single legal UCI move for Black (e.g. e7e5), and nothing else. If there is more than one best move, choose the most challenging for White. Do not explain your move."
                            },
                            {"role": "user", "content": prompt}
                        ]
                    )
                    # Extract only the first valid UCI move from the response
                    uci_candidates = re.findall(r'\b[a-h][1-8][a-h][1-8][qrbn]?\b', response["choices"][0]["message"]["content"])
                    if not uci_candidates:
                        continue  # Try again if no valid UCI move found
                    ai_move_uci = uci_candidates[0]
                    try:
                        ai_move = chess.Move.from_uci(ai_move_uci)
                    except Exception:
                        continue  # Try again if parsing fails
                    if ai_move in board.legal_moves:
                        board.push(ai_move)
                        st.session_state.history.append(ai_move_uci)
                        st.session_state.message = f"AI plays: {ai_move_uci}"
                        break
                    else:
                        if _ == 5:
                            st.session_state.message = (
                                f"AI suggested an illegal move ({ai_move_uci}) six times. The game cannot continue. Please reset."
                            )
                            st.session_state.game_over = True
                else:
                    st.session_state.message = (
                        f"AI failed to provide a legal move after 6 attempts. Please reset."
                    )
                    st.session_state.game_over = True
            except Exception as e:
                st.session_state.message = f"Error with OpenAI API: {e}"
                st.session_state.game_over = True

        render_svg(board)

        # Check game status after AI move
        if display_game_result(board):
            st.session_state.game_over = True

    # Clear move input for next move
    st.rerun()

if st.session_state.message:
    st.info(st.session_state.message)

